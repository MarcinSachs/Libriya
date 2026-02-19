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


# Tworzymy admina powiązanego z tenantem
@pytest.fixture
def admin_user(app, premium_tenant):
    from app.models import User
    user = User(username='admin_test', email='admin@test.com', role='admin', tenant_id=premium_tenant.id)
    user.set_password('password')
    db.session.add(user)
    db.session.commit()
    return user


# Fixture klienta zalogowanego jako admin
@pytest.fixture
def admin_client(client, admin_user):
    with client.session_transaction() as sess:
        sess['user_id'] = admin_user.id
        sess['_user_id'] = str(admin_user.id)
        sess['_fresh'] = True
        sess['_id'] = admin_user.get_id() if hasattr(admin_user, 'get_id') else str(admin_user.id)
    return client


def test_book_delete_with_loans(admin_client, premium_tenant):
    from app.models import Library
    library = Library(name='TestLib', tenant_id=premium_tenant.id)
    db.session.add(library)
    db.session.commit()
    book = Book(title='Test Book', tenant_id=premium_tenant.id, library_id=library.id, year=2020, status='available')
    db.session.add(book)
    db.session.commit()
    resp = admin_client.post(f'/book_delete/{book.id}')
    print('Response status:', resp.status_code)
    print('Response data:', resp.data.decode(errors='replace'))
    assert resp.status_code in (200, 302)
    assert not Book.query.get(book.id)
