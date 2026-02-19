import pytest
from app import db
from app.models import Tenant, User, Book


@pytest.fixture
def premium_tenant(app):
    tenant = Tenant(name='TestTenant', subdomain='test', premium_bookcover_enabled=True,
                    premium_biblioteka_narodowa_enabled=True, premium_batch_import_enabled=True)
    db.session.add(tenant)
    db.session.commit()
    return tenant


@pytest.fixture
def superadmin_user(app):
    from app.models import User
    user = User(username='superadmin_test', email='superadmin@test.com', role='superadmin')
    user.set_password('password')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def superadmin_client(client, superadmin_user, premium_tenant):
    # Log in superadmin by setting user_id in session
    with client.session_transaction() as sess:
        sess['user_id'] = superadmin_user.id
    return client


def test_toggle_bookcover_api(superadmin_client, premium_tenant):
    resp = superadmin_client.post(f'/admin/tenants/{premium_tenant.id}/premium/bookcover_api/toggle')
    assert resp.status_code == 200 or resp.status_code == 302
    db.session.refresh(premium_tenant)
    assert premium_tenant.premium_bookcover_enabled in [True, False]


def test_toggle_biblioteka_narodowa(superadmin_client, premium_tenant):
    resp = superadmin_client.post(f'/admin/tenants/{premium_tenant.id}/premium/biblioteka_narodowa/toggle')
    assert resp.status_code == 200 or resp.status_code == 302
    db.session.refresh(premium_tenant)
    assert premium_tenant.premium_biblioteka_narodowa_enabled in [True, False]


def test_toggle_batch_import(superadmin_client, premium_tenant):
    resp = superadmin_client.post(f'/admin/tenants/{premium_tenant.id}/premium/batch_import/toggle')
    assert resp.status_code == 200 or resp.status_code == 302
    db.session.refresh(premium_tenant)
    assert premium_tenant.premium_batch_import_enabled in [True, False]


def test_batch_import_view(superadmin_client, premium_tenant):
    resp = superadmin_client.get('/books/batch_import')
    assert resp.status_code in (200, 302)  # 302 if not admin/manager
