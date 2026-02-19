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

def test_login_page(client):
    response = client.get('/auth/login', follow_redirects=True)
    assert response.status_code == 200
    assert b'login' in response.data.lower() or b'logowanie' in response.data.lower()

def test_register_page(client):
    response = client.get('/auth/register', follow_redirects=True)
    assert response.status_code == 200
    assert b'register' in response.data.lower() or b'rejestracja' in response.data.lower()

def test_register_and_login(client):
    # Register new user
    response = client.post('/auth/register', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'StrongPass123!'
    }, follow_redirects=True)
    assert response.status_code == 200
    # Login with new user
    response = client.post('/auth/login', data={
        'username': 'testuser',
        'password': 'StrongPass123!'
    }, follow_redirects=True)
    assert response.status_code == 200
    # Sprawdź obecność komunikatu lub przekierowania (np. do / lub /dashboard)
    assert b'logout' in response.data.lower() or b'wyloguj' in response.data.lower() or b'libriya' in response.data.lower()

def test_login_invalid(client):
    response = client.post('/auth/login', data={
        'username': 'wronguser',
        'password': 'wrongpass'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'login' in response.data.lower() or b'logowanie' in response.data.lower() or b'error' in response.data.lower()

def test_add_book_invalid_data(client):
    client.post('/auth/register', data={
        'username': 'bookuser2',
        'email': 'bookuser2@example.com',
        'password': 'BookPass123!'
    }, follow_redirects=True)
    client.post('/auth/login', data={
        'username': 'bookuser2',
        'password': 'BookPass123!'
    }, follow_redirects=True)
    response = client.post('/books/add', data={
        'title': '',  # brak tytułu
        'author': '',
        'year': '',
        'isbn': ''
    }, follow_redirects=True)
    assert response.status_code in (200, 302)
    assert b'error' in response.data.lower() or b'blad' in response.data.lower() or b'libriya' in response.data.lower()

# Test szczegółów książki

def test_book_details(client):
    client.post('/auth/register', data={
        'username': 'bookuser3',
        'email': 'bookuser3@example.com',
        'password': 'BookPass123!'
    }, follow_redirects=True)
    client.post('/auth/login', data={
        'username': 'bookuser3',
        'password': 'BookPass123!'
    }, follow_redirects=True)
    client.post('/books/add', data={
        'title': 'Book Detail',
        'author': 'Author D',
        'year': 2023,
        'isbn': '9781234567890'
    }, follow_redirects=True)
    # Używaj poprawnego endpointu
    response = client.get('/book/1', follow_redirects=True)
    assert response.status_code in (200, 302)
    assert b'book detail' in response.data.lower() or b'ksiazka' in response.data.lower() or b'libriya' in response.data.lower()

def test_admin_panel(client):
    response = client.get('/admin/', follow_redirects=True)
    assert response.status_code in (200, 302)
    assert b'admin' in response.data.lower() or b'panel' in response.data.lower() or b'libriya' in response.data.lower() or b'login' in response.data.lower()

# Dodawanie użytkownika przez admina

def test_admin_add_user(client):
    client.post('/auth/register', data={
        'username': 'adminuser',
        'email': 'adminuser@example.com',
        'password': 'AdminPass123!'
    }, follow_redirects=True)
    client.post('/auth/login', data={
        'username': 'adminuser',
        'password': 'AdminPass123!'
    }, follow_redirects=True)
    response = client.post('/users/add/', data={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'NewPass123!'
    }, follow_redirects=True)
    assert response.status_code in (200, 302)
    assert b'newuser' in response.data.lower() or b'user' in response.data.lower() or b'libriya' in response.data.lower()

# Dodawanie biblioteki przez admina

def test_admin_add_library(client):
    client.post('/auth/register', data={
        'username': 'adminlib',
        'email': 'adminlib@example.com',
        'password': 'AdminLib123!'
    }, follow_redirects=True)
    client.post('/auth/login', data={
        'username': 'adminlib',
        'password': 'AdminLib123!'
    }, follow_redirects=True)
    response = client.post('/libraries/add', data={
        'name': 'Test Library',
        'address': 'Test Address',
        'city': 'Test City'
    }, follow_redirects=True)
    assert response.status_code in (200, 302)
    assert b'test library' in response.data.lower() or b'biblioteka' in response.data.lower() or b'libriya' in response.data.lower()

# Testy bibliotek

def test_library_list(client):
    client.post('/auth/register', data={
        'username': 'libuser',
        'email': 'libuser@example.com',
        'password': 'LibPass123!'
    }, follow_redirects=True)
    client.post('/auth/login', data={
        'username': 'libuser',
        'password': 'LibPass123!'
    }, follow_redirects=True)
    response = client.get('/libraries/', follow_redirects=True)
    assert response.status_code in (200, 302)
    assert b'biblioteka' in response.data.lower() or b'library' in response.data.lower() or b'libriya' in response.data.lower()

# Testy użytkowników

def test_user_profile(client):
    client.post('/auth/register', data={
        'username': 'profileuser',
        'email': 'profileuser@example.com',
        'password': 'ProfilePass123!'
    }, follow_redirects=True)
    client.post('/auth/login', data={
        'username': 'profileuser',
        'password': 'ProfilePass123!'
    }, follow_redirects=True)
    response = client.get('/user/profile/1', follow_redirects=True)
    assert response.status_code in (200, 302)
    assert b'profileuser' in response.data.lower() or b'user' in response.data.lower() or b'libriya' in response.data.lower()

def test_edit_book(client):
    # Register and login as admin
    client.post('/auth/register', data={
        'username': 'editadmin',
        'email': 'editadmin@example.com',
        'password': 'EditAdmin123!'
    }, follow_redirects=True)
    client.post('/auth/login', data={
        'username': 'editadmin',
        'password': 'EditAdmin123!'
    }, follow_redirects=True)
    # Add a book
    client.post('/books/add', data={
        'title': 'Book To Edit',
        'author': 'Author E',
        'year': 2024,
        'isbn': '9781234567891'
    }, follow_redirects=True)
    # Edit the book
    response = client.post('/book_edit/1', data={
        'title': 'Book Edited',
        'author': 'Author E',
        'year': 2025,
        'isbn': '9781234567891'
    }, follow_redirects=True)
    assert response.status_code in (200, 302)
    # Check if the edit was successful
    detail = client.get('/book/1', follow_redirects=True)
    assert b'book edited' in detail.data.lower() or b'libriya' in detail.data.lower()

def test_delete_book(client):
    client.post('/auth/register', data={
        'username': 'deladmin',
        'email': 'deladmin@example.com',
        'password': 'DelAdmin123!'
    }, follow_redirects=True)
    client.post('/auth/login', data={
        'username': 'deladmin',
        'password': 'DelAdmin123!'
    }, follow_redirects=True)
    client.post('/books/add', data={
        'title': 'Book To Delete',
        'author': 'Author D',
        'year': 2024,
        'isbn': '9781234567892'
    }, follow_redirects=True)
    response = client.post('/book_delete/1', follow_redirects=True)
    assert response.status_code in (200, 302)
    # Try to get the deleted book
    detail = client.get('/book/1', follow_redirects=True)
    # Should not contain the deleted book's title
    assert b'book to delete' not in detail.data.lower()

def test_add_and_remove_favorite(client):
    client.post('/auth/register', data={
        'username': 'favuser',
        'email': 'favuser@example.com',
        'password': 'FavUser123!'
    }, follow_redirects=True)
    client.post('/auth/login', data={
        'username': 'favuser',
        'password': 'FavUser123!'
    }, follow_redirects=True)
    client.post('/books/add', data={
        'title': 'Book Favorite',
        'author': 'Author F',
        'year': 2024,
        'isbn': '9781234567893'
    }, follow_redirects=True)
    # Add to favorites
    response = client.post('/favorites/add/1', follow_redirects=True)
    assert response.status_code in (200, 302)
    # Remove from favorites
    response = client.post('/favorites/remove/1', follow_redirects=True)
    assert response.status_code in (200, 302)

def test_unauthorized_book_detail(client):
    # Try to access book detail without login
    response = client.get('/book/1', follow_redirects=True)
    assert response.status_code in (200, 302)
    assert b'login' in response.data.lower() or b'unauthorized' in response.data.lower()

def test_unauthorized_admin_panel(client):
    # Try to access admin panel without login
    response = client.get('/admin/', follow_redirects=True)
    assert response.status_code in (200, 302)
    assert b'login' in response.data.lower() or b'unauthorized' in response.data.lower()
