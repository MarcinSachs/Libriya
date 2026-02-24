import pytest
from app import db
from app.models import User, Tenant, Library


def login(client, username, password='password'):
    return client.post('/auth/login/', data={'email_or_username': username, 'password': password}, follow_redirects=True)


def test_library_limit_prevents_add_and_shows_flash(client, app):
    # create a tenant with maximum 1 library
    t = Tenant(name='TL', subdomain='tlimit', max_libraries=1)
    db.session.add(t)
    db.session.commit()

    # add an existing library to hit the limit
    lib = Library(name='Existing', tenant_id=t.id)
    db.session.add(lib)
    db.session.commit()

    # create admin user under this tenant
    admin = User(username='adminl', email='adminl@example.com', role='admin', tenant_id=t.id)
    admin.is_email_verified = True
    admin.set_password('password')
    db.session.add(admin)
    db.session.commit()

    # login as admin
    rv = login(client, admin.email)
    assert b'Please log in' not in rv.data

    # GET add page should redirect back with limit flash
    get = client.get('/libraries/add', follow_redirects=True)
    assert get.status_code == 200
    # we should still land on the libraries listing and see the error message
    assert b'Manage Libraries' in get.data
    assert b'maximum number of libraries' in get.data.lower()

    # POST to add should also trigger the same flash
    post_data = {'name': 'Another', 'loan_overdue_days': 10}
    post = client.post('/libraries/add', data=post_data, follow_redirects=True)
    assert post.status_code == 200
    assert b'Manage Libraries' in post.data
    assert b'maximum number of libraries' in post.data.lower()


@pytest.mark.parametrize('max_libraries', (-1, None))
def test_unlimited_libraries_allows_add(client, app, max_libraries):
    # tenant with unlimited libraries should not hit the check
    t = Tenant(name='TU', subdomain=f'tu{max_libraries}', max_libraries=max_libraries)
    db.session.add(t)
    db.session.commit()

    admin = User(username='admu', email=f'admu{max_libraries}@example.com', role='admin', tenant_id=t.id)
    admin.is_email_verified = True
    admin.set_password('password')
    db.session.add(admin)
    db.session.commit()

    # login and access add page without redirect
    login(client, admin.email)
    resp = client.get('/libraries/add')
    assert resp.status_code == 200
    assert b'Add Library' in resp.data
