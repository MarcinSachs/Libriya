import pytest
from app import create_app, db

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

# --- CRUD biblioteki ---
def test_library_crud(client):
    client.post('/auth/register', data={
        'username': 'libadmin',
        'email': 'libadmin@example.com',
        'password': 'LibAdmin123!'
    }, follow_redirects=True)
    client.post('/auth/login', data={
        'username': 'libadmin',
        'password': 'LibAdmin123!'
    }, follow_redirects=True)
    # Dodawanie
    response = client.post('/libraries/add', data={
        'name': 'LibTest',
        'address': 'Test Address',
        'city': 'Test City'
    }, follow_redirects=True)
    assert response.status_code in (200, 302)
    # Lista
    response = client.get('/libraries/', follow_redirects=True)
    assert response.status_code in (200, 302)
    # Edycja
    response = client.post('/libraries/edit/1', data={
        'name': 'LibTestEdit',
        'address': 'Edit Address',
        'city': 'Edit City'
    }, follow_redirects=True)
    assert response.status_code in (200, 302)
    # Usuwanie
    response = client.post('/libraries/delete/1', follow_redirects=True)
    assert response.status_code in (200, 302)

# --- CRUD użytkownik ---
def test_user_crud(client):
    client.post('/auth/register', data={
        'username': 'useradmin',
        'email': 'useradmin@example.com',
        'password': 'UserAdmin123!'
    }, follow_redirects=True)
    client.post('/auth/login', data={
        'username': 'useradmin',
        'password': 'UserAdmin123!'
    }, follow_redirects=True)
    # Dodawanie
    response = client.post('/users/add/', data={
        'username': 'UserTest',
        'email': 'usertest@example.com',
        'password': 'UserTest123!'
    }, follow_redirects=True)
    assert response.status_code in (200, 302)
    # Lista
    response = client.get('/users/', follow_redirects=True)
    assert response.status_code in (200, 302)
    # Edycja
    response = client.post('/users/edit/1', data={
        'username': 'UserTestEdit',
        'email': 'usertestedit@example.com',
        'password': 'UserTestEdit123!'
    }, follow_redirects=True)
    assert response.status_code in (200, 302)
    # Usuwanie
    response = client.post('/users/delete/1', follow_redirects=True)
    assert response.status_code in (200, 302)
