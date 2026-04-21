from app import db
from app.models import Genre, Tenant, Library, User, UserLibrary
from datetime import datetime


def login(client, username, password='password'):
    return client.post('/auth/login/', data={'email_or_username': username, 'password': password})


def test_manager_adds_user_assigned_to_managed_libraries(client, app):
    with app.app_context():
        # Setup tenant, library and manager
        t = Tenant(name='T1', subdomain='t1')
        db.session.add(t)
        db.session.commit()

        lib = Library(name='Lib1', tenant_id=t.id)
        db.session.add(lib)
        db.session.commit()

        mgr = User(username='mgr', email='mgr@t1.example', role='manager', tenant_id=t.id)
        mgr.set_password('password')
        mgr.is_email_verified = True
        db.session.add(mgr)
        db.session.flush()
        db.session.add(UserLibrary(user_id=mgr.id, library_id=lib.id, library_role='manager'))
        db.session.commit()

        # Login as manager
        login(client, 'mgr')

        # Add a new user via manager - should be automatically assigned to manager's libraries
        res = client.post('/users/add/', data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'Str0ngPass!23',
            'confirm_password': 'Str0ngPass!23'
        }, follow_redirects=True)

        assert res.status_code in (200, 302)
        new_user = User.query.filter_by(username='newuser').first()
        assert new_user is not None
        assert lib in new_user.libraries


def test_admin_edits_user_role_and_libraries(client, app):
    with app.app_context():
        t = Tenant(name='T2', subdomain='t2')
        db.session.add(t)
        db.session.commit()

        lib_a = Library(name='A', tenant_id=t.id)
        lib_b = Library(name='B', tenant_id=t.id)
        db.session.add_all([lib_a, lib_b])
        db.session.commit()

        admin = User(username='admin1', email='admin1@t2.example', role='admin', tenant_id=t.id)
        admin.set_password('password')
        admin.is_email_verified = True
        db.session.add(admin)

        target = User(username='u1', email='u1@t2.example', role='user', tenant_id=t.id)
        target.set_password('password')
        target.is_email_verified = True
        db.session.add(target)
        db.session.flush()
        db.session.add(UserLibrary(user_id=target.id, library_id=lib_a.id, library_role='member'))
        db.session.commit()

        # login as admin
        login(client, 'admin1')

        # change role and reassign to lib_b
        res = client.post(f'/users/edit/{target.id}', data={
            'email': 'u1-new@t2.example',
            f'lib_role_{lib_a.id}': 'none',
            f'lib_role_{lib_b.id}': 'manager'
        }, follow_redirects=True)
        assert res.status_code in (200, 302)

        updated = User.query.get(target.id)
        assert updated.email == 'u1-new@t2.example'
        assert updated.role == 'manager'
        assert lib_b in updated.libraries
        assert lib_a not in updated.libraries


def test_admin_promotes_user_from_member_to_manager_in_second_library(client, app):
    with app.app_context():
        t = Tenant(name='T5', subdomain='t5')
        db.session.add(t)
        db.session.commit()

        lib1 = Library(name='L1', tenant_id=t.id)
        lib2 = Library(name='L2', tenant_id=t.id)
        db.session.add_all([lib1, lib2])
        db.session.commit()

        admin = User(username='admin5', email='admin5@t5.example', role='admin', tenant_id=t.id)
        admin.set_password('password')
        admin.is_email_verified = True
        db.session.add(admin)

        target = User(username='u5', email='u5@t5.example', role='manager', tenant_id=t.id)
        target.set_password('password')
        target.is_email_verified = True
        db.session.add(target)
        db.session.flush()
        db.session.add(UserLibrary(user_id=target.id, library_id=lib1.id, library_role='manager'))
        db.session.add(UserLibrary(user_id=target.id, library_id=lib2.id, library_role='member'))
        db.session.commit()

        g = Genre(name='Science')
        db.session.add(g)
        db.session.commit()

        login(client, 'admin5')
        res = client.post(f'/users/edit/{target.id}', data={
            'email': 'u5@t5.example',
            f'lib_role_{lib1.id}': 'manager',
            f'lib_role_{lib2.id}': 'manager'
        }, follow_redirects=True)
        assert res.status_code in (200, 302)

        # After edit, target should be manager in both libraries and can add books in lib2.
        login(client, 'u5')
        get = client.get('/books/add/')
        assert get.status_code == 200
        assert str(lib2.id) in get.get_data(as_text=True)

        post = client.post('/books/add/', data={
            'isbn': '1234567890123',
            'title': 'Lib2 Book',
            'author': 'Test Author',
            'library': str(lib2.id),
            'genres': [str(g.id)],
            'year': 2020,
            'description': 'Test',
            'csrf_token': ''
        }, follow_redirects=True)
        assert post.status_code == 200
        from app.models import Book
        book = Book.query.filter_by(title='Lib2 Book').first()
        assert book is not None
        assert book.library_id == lib2.id


def test_admin_edit_of_logged_in_user_library_role_invalidates_user_cache(client, app):
    with app.app_context():
        t = Tenant(name='T6', subdomain='t6')
        db.session.add(t)
        db.session.commit()

        lib1 = Library(name='L1', tenant_id=t.id)
        lib2 = Library(name='L2', tenant_id=t.id)
        db.session.add_all([lib1, lib2])
        db.session.commit()

        admin = User(username='admin6', email='admin6@t6.example', role='admin', tenant_id=t.id)
        admin.set_password('password')
        admin.is_email_verified = True
        db.session.add(admin)

        target = User(username='u6', email='u6@t6.example', role='manager', tenant_id=t.id)
        target.set_password('password')
        target.is_email_verified = True
        db.session.add(target)
        db.session.flush()
        db.session.add(UserLibrary(user_id=target.id, library_id=lib1.id, library_role='manager'))
        db.session.add(UserLibrary(user_id=target.id, library_id=lib2.id, library_role='member'))
        db.session.commit()

        target_client = app.test_client()
        admin_client = app.test_client()

        # Initial login as target user to populate cached user object.
        resp = target_client.post(
            '/auth/login/', data={'email_or_username': target.email, 'password': 'password'}, follow_redirects=True)
        assert resp.status_code == 200
        initial = target_client.get('/books/add/')
        assert lib1.name in initial.get_data(as_text=True)
        assert lib2.name not in initial.get_data(as_text=True)

        # Admin updates the target user's second library to manager.
        resp2 = admin_client.post(
            '/auth/login/', data={'email_or_username': admin.email, 'password': 'password'}, follow_redirects=True)
        assert resp2.status_code == 200
        edit = admin_client.post(f'/users/edit/{target.id}', data={
            'email': target.email,
            f'lib_role_{lib1.id}': 'manager',
            f'lib_role_{lib2.id}': 'manager'
        }, follow_redirects=True)
        assert edit.status_code in (200, 302)

        # Target user should now see lib2 as manageable.
        refreshed = target_client.get('/books/add/')
        assert refreshed.status_code == 200
        assert lib2.name in refreshed.get_data(as_text=True)

        g = Genre(name='MyGenre')
        db.session.add(g)
        db.session.commit()
        post = target_client.post('/books/add/', data={
            'isbn': '9781234567897',
            'title': 'Cache Fix Book',
            'author': 'Author X',
            'library': str(lib2.id),
            'genres': [str(g.id)],
            'year': 2023,
            'description': 'Cache invalidation test',
            'csrf_token': ''
        }, follow_redirects=True)
        assert post.status_code == 200
        from app.models import Book
        assert Book.query.filter_by(title='Cache Fix Book', library_id=lib2.id).first() is not None


def test_manager_cannot_promote_user_to_admin(client, app):
    with app.app_context():
        t = Tenant(name='T3', subdomain='t3')
        db.session.add(t)
        db.session.commit()

        lib = Library(name='LM', tenant_id=t.id)
        db.session.add(lib)
        db.session.commit()

        mgr = User(username='mgr2', email='mgr2@t3.example', role='manager', tenant_id=t.id)
        mgr.set_password('password')
        mgr.is_email_verified = True
        db.session.add(mgr)
        db.session.flush()
        db.session.add(UserLibrary(user_id=mgr.id, library_id=lib.id, library_role='manager'))

        target = User(username='plain', email='plain@t3.example', role='user', tenant_id=t.id)
        target.set_password('password')
        target.is_email_verified = True
        db.session.add(target)
        db.session.flush()
        db.session.add(UserLibrary(user_id=target.id, library_id=lib.id, library_role='member'))
        db.session.commit()

        login(client, 'mgr2')

        res = client.post(f'/users/edit/{target.id}', data={'email': target.email,
                          'role': 'admin', 'libraries': [str(lib.id)]}, follow_redirects=True)
        assert res.status_code in (200, 302)

        tuser = User.query.get(target.id)
        # role should remain unchanged
        assert tuser.role == 'user'


def test_delete_user_rules_and_manager_scope(client, app):
    with app.app_context():
        t = Tenant(name='T4', subdomain='t4')
        db.session.add(t)
        db.session.commit()

        lib1 = Library(name='L1', tenant_id=t.id)
        lib2 = Library(name='L2', tenant_id=t.id)
        db.session.add_all([lib1, lib2])
        db.session.commit()

        admin = User(username='admin2', email='admin2@t4.example', role='admin', tenant_id=t.id)
        admin.set_password('password')
        admin.is_email_verified = True
        db.session.add(admin)

        mgr = User(username='mgr3', email='mgr3@t4.example', role='manager', tenant_id=t.id)
        mgr.set_password('password')
        mgr.is_email_verified = True
        db.session.add(mgr)
        db.session.flush()
        db.session.add(UserLibrary(user_id=mgr.id, library_id=lib1.id, library_role='manager'))

        u_in = User(username='uin', email='uin@t4.example', role='user', tenant_id=t.id)
        u_in.set_password('password')
        u_in.is_email_verified = True
        db.session.add(u_in)
        db.session.flush()
        db.session.add(UserLibrary(user_id=u_in.id, library_id=lib1.id, library_role='member'))

        u_out = User(username='uout', email='uout@t4.example', role='user', tenant_id=t.id)
        u_out.set_password('password')
        u_out.is_email_verified = True
        db.session.add(u_out)
        db.session.flush()
        db.session.add(UserLibrary(user_id=u_out.id, library_id=lib2.id, library_role='member'))

        db.session.commit()

        # manager deletes user in his library -> allowed
        login(client, 'mgr3')
        del_resp = client.post(f'/users/delete/{u_in.id}', follow_redirects=True)
        assert del_resp.status_code in (200, 302)
        assert User.query.get(u_in.id) is None

        # manager tries to delete user outside his libraries -> blocked
        del_resp2 = client.post(f'/users/delete/{u_out.id}', follow_redirects=True)
        assert del_resp2.status_code in (200, 302)
        assert User.query.get(u_out.id) is not None

        # admin cannot delete self
        login(client, 'admin2')
        resp = client.post(f'/users/delete/{admin.id}', follow_redirects=True)
        assert resp.status_code in (200, 302)
        assert User.query.get(admin.id) is not None

        # admin cannot delete another admin user
        other_admin = User(username='admin3', email='admin3@t4.example', role='admin', tenant_id=t.id)
        other_admin.set_password('password')
        other_admin.is_email_verified = True
        db.session.add(other_admin)
        db.session.commit()

        resp2 = client.post(f'/users/delete/{other_admin.id}', follow_redirects=True)
        assert resp2.status_code in (200, 302)
        assert User.query.get(other_admin.id) is not None
