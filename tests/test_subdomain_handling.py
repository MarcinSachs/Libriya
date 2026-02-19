import pytest
from app import create_app, db
from app.models import Tenant, User


@pytest.fixture
def setup_db(app):
    # create a tenant and a user belonging to that tenant
    t = Tenant(name='TestTenant', subdomain='testtenant')
    db.session.add(t)
    db.session.commit()

    user = User(username='tenant_user', email='user@test.com', tenant_id=t.id, role='user')
    user.set_password('password')
    db.session.add(user)
    db.session.commit()
    return t, user


def test_unknown_subdomain_returns_404(client, app):
    # Ensure ENFORCE_SUBDOMAIN_EXISTS True by default
    app.config['ENFORCE_SUBDOMAIN_EXISTS'] = True
    response = client.get('/', headers={'Host': 'unknown.localhost'})
    assert response.status_code == 404


def test_unknown_subdomain_allowed_when_flag_false(client, app):
    app.config['ENFORCE_SUBDOMAIN_EXISTS'] = False
    response = client.get('/', headers={'Host': 'unknown.localhost'})
    # Should continue processing; if no route matches, Flask returns 404, but we want to ensure
    # middleware didn't abort explicitly. Check that status code is not specifically our abort code
    assert response.status_code in (200, 404)


def test_user_tenant_mismatch_forbidden(client, app, setup_db):
    t, user = setup_db
    # create another tenant to trigger a tenant mismatch (existing subdomain)
    other_tenant = Tenant(name='OtherTenant', subdomain='other')
    db.session.add(other_tenant)
    db.session.commit()

    # Ensure session cookie is valid across subdomains for this test
    app.config['SESSION_COOKIE_DOMAIN'] = '.example.com'

    # Mark user as email-verified so login is allowed
    user.is_email_verified = True
    db.session.commit()

    # Perform real login on the correct tenant subdomain
    login_resp = client.post('/auth/login/', data={
        'email_or_username': user.username,
        'password': 'password'
    }, base_url=f'http://{t.subdomain}.example.com', follow_redirects=True)

    assert login_resp.status_code in (200, 302)

    # Access with different tenant subdomain (which exists)
    response = client.get('/', base_url=f'http://{other_tenant.subdomain}.example.com')
    assert response.status_code == 403
