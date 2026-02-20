from app import db
from app.models import Tenant, Library, User
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
        mgr.libraries.append(lib)
        db.session.add(mgr)
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
        target.libraries.append(lib_a)
        db.session.add(target)
        db.session.commit()

        # login as admin
        login(client, 'admin1')

        # change role and reassign to lib_b
        res = client.post(f'/users/edit/{target.id}', data={
            'email': 'u1-new@t2.example',
            'role': 'manager',
            'libraries': [str(lib_b.id)]
        }, follow_redirects=True)
        assert res.status_code in (200, 302)

        updated = User.query.get(target.id)
        assert updated.email == 'u1-new@t2.example'
        assert updated.role == 'manager'
        assert lib_b in updated.libraries
        assert lib_a not in updated.libraries


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
        mgr.libraries.append(lib)
        db.session.add(mgr)

        target = User(username='plain', email='plain@t3.example', role='user', tenant_id=t.id)
        target.set_password('password')
        target.is_email_verified = True
        target.libraries.append(lib)
        db.session.add(target)
        db.session.commit()

        login(client, 'mgr2')

        res = client.post(f'/users/edit/{target.id}', data={'email': target.email, 'role': 'admin', 'libraries': [str(lib.id)]}, follow_redirects=True)
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
        mgr.libraries.append(lib1)
        db.session.add(mgr)

        u_in = User(username='uin', email='uin@t4.example', role='user', tenant_id=t.id)
        u_in.set_password('password')
        u_in.is_email_verified = True
        u_in.libraries.append(lib1)

        u_out = User(username='uout', email='uout@t4.example', role='user', tenant_id=t.id)
        u_out.set_password('password')
        u_out.is_email_verified = True
        u_out.libraries.append(lib2)

        db.session.add_all([u_in, u_out])
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
