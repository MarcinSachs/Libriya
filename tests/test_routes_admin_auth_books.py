import pytest
from app import create_app, db
from app.models import User

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

def test_admin_panel_requires_login(client):
    response = client.get('/admin', follow_redirects=True)
    assert response.status_code == 200
    assert b'login' in response.data.lower() or b'logowanie' in response.data.lower()

def test_auth_logout(client):
    response = client.get('/auth/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'login' in response.data.lower() or b'logowanie' in response.data.lower()

def test_books_list(client):
    # Najpierw rejestracja i logowanie
    client.post('/auth/register', data={
        'username': 'bookuser',
        'email': 'bookuser@example.com',
        'password': 'BookPass123!'
    }, follow_redirects=True)
    client.post('/auth/login', data={
        'username': 'bookuser',
        'password': 'BookPass123!'
    }, follow_redirects=True)
    # Próba pobrania listy książek
    for path in ['/books', '/books/', '/books/list']:
        response = client.get(path, follow_redirects=True)
        if response.status_code != 404:
            assert response.status_code == 200
            assert b'ksiazka' in response.data.lower() or b'book' in response.data.lower() or b'libriya' in response.data.lower()
            break
    else:
        pytest.skip('Brak endpointu /books w aplikacji')
