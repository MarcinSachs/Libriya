import pytest
from app import db
from app.models import User, Tenant, Library, SharedLink, Book


def login(client, username, password='password'):
    return client.post('/auth/login/', data={'email_or_username': username, 'password': password}, follow_redirects=True)


def test_share_link_generation_and_public_access(client, app):
    # setup tenant, library, admin
    t = Tenant(name='ShareTenant', subdomain='st')
    db.session.add(t)
    db.session.commit()
    lib = Library(name='ShareLib', tenant_id=t.id)
    db.session.add(lib)
    db.session.commit()
    admin = User(username='shareadm', email='sa@example.com', role='admin', tenant_id=t.id)
    admin.is_email_verified = True
    admin.set_password('password')
    db.session.add(admin)
    db.session.commit()

    # create some books
    book1 = Book(title='First', library_id=lib.id, tenant_id=t.id, year=2001)
    book2 = Book(title='Second', library_id=lib.id, tenant_id=t.id, year=2002)
    db.session.add_all([book1, book2])
    db.session.commit()

    login(client, admin.email)

    # generate link (no expiry)
    resp = client.post(f'/libraries/{lib.id}/share', data={'expires_at': ''})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success']
    token = data['token']
    assert token
    url = data['url']

    # public access list
    public = client.get(f'/share/{token}/')
    assert public.status_code == 200
    assert b'First' in public.data and b'Second' in public.data

    # public access book detail
    detail = client.get(f'/share/{token}/book/{book1.id}')
    assert detail.status_code == 200
    assert b'First' in detail.data

    # invalid token
    assert client.get('/share/invalid/').status_code == 404

    # deactivate via API, public page should 404 afterwards
    resp2 = client.post(f'/libraries/{lib.id}/share/deactivate')
    assert resp2.status_code == 200
    data2 = resp2.get_json()
    assert data2.get('success')
    assert client.get(f'/share/{token}/').status_code == 404

    # expire link and check (should still 404)
    link = SharedLink.query.filter_by(token=token).first()
    link.expires_at = link.created_at  # expire immediately
    db.session.commit()
    assert client.get(f'/share/{token}/').status_code == 404
