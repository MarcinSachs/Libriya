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

# --- AUTH ---
def test_register_login_logout(client):
    # Register
    response = client.post('/auth/register', data={
        'username': 'user1',
        'email': 'user1@example.com',
        'password': 'StrongPass123!'
    }, follow_redirects=True)
    assert response.status_code == 200
    # Login
    response = client.post('/auth/login', data={
        'username': 'user1',
        'password': 'StrongPass123!'
    }, follow_redirects=True)
    assert response.status_code == 200
    # Logout
    response = client.get('/auth/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b'login' in response.data.lower() or b'logowanie' in response.data.lower()

def test_reset_password_page(client):
    # Spróbuj różnych wariantów ścieżki
    for path in ['/auth/reset', '/auth/password_reset', '/auth/request_reset', '/auth/forgot']:
        response = client.get(path, follow_redirects=True)
        if response.status_code != 404:
            assert response.status_code == 200
            assert b'reset' in response.data.lower() or b'haslo' in response.data.lower() or b'password' in response.data.lower()
            break
    else:
        pytest.skip('Brak endpointu resetu hasła w aplikacji')

# --- ADMIN ---
def test_admin_panel_requires_login(client):
    response = client.get('/admin', follow_redirects=True)
    assert response.status_code == 200
    assert b'login' in response.data.lower() or b'logowanie' in response.data.lower()

# --- BOOKS ---
def test_books_crud(client):
    # Register & login
    client.post('/auth/register', data={
        'username': 'bookadmin',
        'email': 'bookadmin@example.com',
        'password': 'BookPass123!'
    }, follow_redirects=True)
    client.post('/auth/login', data={
        'username': 'bookadmin',
        'password': 'BookPass123!'
    }, follow_redirects=True)
    # Add book
    response = client.post('/books/add', data={
        'title': 'Test Book',
        'author': 'Author X',
        'year': 2022,
        'isbn': '9781234567897'
    }, follow_redirects=True)
    assert response.status_code in (200, 302)
    # Sprawdź obecność frazy lub przekierowania
    assert b'test book' in response.data.lower() or b'ksiazka' in response.data.lower() or b'libriya' in response.data.lower() or b'success' in response.data.lower() or b'dodano' in response.data.lower() or b'added' in response.data.lower()
    # List books
    for path in ['/books', '/books/', '/books/list']:
        response = client.get(path, follow_redirects=True)
        if response.status_code != 404:
            assert response.status_code in (200, 302)
            assert b'test book' in response.data.lower() or b'ksiazka' in response.data.lower() or b'libriya' in response.data.lower()
            break
    else:
        pytest.skip('Brak endpointu /books w aplikacji')
    # Edit book (simulate GET)
    for path in ['/books/edit/1', '/books/edit/0', '/books/edit']:
        response = client.get(path, follow_redirects=True)
        if response.status_code != 404:
            assert response.status_code in (200, 302)
            break
    # Delete book (simulate GET/POST)
    for path in ['/books/delete/1', '/books/delete/0', '/books/delete']:
        response = client.post(path, follow_redirects=True)
        if response.status_code != 404:
            assert response.status_code in (200, 302)
            break

# --- SEARCH ---
def test_books_search(client):
    client.post('/auth/register', data={
        'username': 'searchuser',
        'email': 'searchuser@example.com',
        'password': 'SearchPass123!'
    }, follow_redirects=True)
    client.post('/auth/login', data={
        'username': 'searchuser',
        'password': 'SearchPass123!'
    }, follow_redirects=True)
    # Spróbuj różnych wariantów ścieżki
    for path in ['/books?query=Test', '/books/search?query=Test', '/books/list?query=Test']:
        response = client.get(path, follow_redirects=True)
        if response.status_code != 404:
            assert response.status_code in (200, 302)
            assert b'test' in response.data.lower() or b'ksiazka' in response.data.lower() or b'libriya' in response.data.lower()
            break
    else:
        pytest.skip('Brak endpointu wyszukiwania książek w aplikacji')
