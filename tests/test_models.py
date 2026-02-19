import pytest
from app.models import User, Tenant, Book, Author, Genre, Loan, Library, Location
from werkzeug.security import check_password_hash

class DummyDB:
    # Minimal dummy for db.Model inheritance
    pass

def test_user_password_set_and_check():
    user = User()
    user.set_password('supersecret')
    assert user.password_hash != 'supersecret'
    assert user.check_password('supersecret')
    assert not user.check_password('wrongpass')

def test_user_roles():
    user = User(role='user')
    admin = User(role='admin', tenant_id=1)
    superadmin = User(role='superadmin')
    legacy_superadmin = User(role='admin', tenant_id=None)

    assert not user.is_admin
    assert admin.is_admin
    assert superadmin.is_admin
    assert superadmin.is_super_admin
    assert admin.is_tenant_admin
    assert legacy_superadmin.is_super_admin_old

def test_tenant_premium_features():
    tenant = Tenant(premium_bookcover_enabled=True, premium_biblioteka_narodowa_enabled=False)
    assert tenant.is_premium_enabled('bookcover_api')
    assert not tenant.is_premium_enabled('biblioteka_narodowa')
    assert 'bookcover_api' in tenant.get_enabled_premium_features()
    assert 'biblioteka_narodowa' not in tenant.get_enabled_premium_features()

def test_book_str():
    author = Author(name='J.K. Rowling')
    genre = Genre(name='Fantasy')
    book = Book(title='Harry Potter', year=1997)
    book.authors.append(author)
    book.genres.append(genre)
    s = str(book)
    assert 'Harry Potter' in s
    assert 'J.K. Rowling' in s
    assert 'Fantasy' in s

def test_library_str():
    lib = Library(name='Central Library', tenant_id=1)
    assert str(lib) == 'Central Library'

def test_genre_str():
    genre = Genre(name='Science Fiction')
    assert str(genre) == 'Science Fiction'

def test_author_str():
    author = Author(name='Isaac Asimov')
    assert str(author) == 'Isaac Asimov'

def test_location_str():
    loc = Location(room='Main Hall', section='Fiction', shelf='A', notes='Top shelf')
    s = str(loc)
    assert 'Main Hall' in s
    assert 'Fiction' in s
    assert 'Shelf A' in s
    assert '(Top shelf)' in s
    # Test fallback
    loc2 = Location()
    assert str(loc2) == 'No location'

def test_loan_str():
    user = User(username='paul')
    book = Book(title='Dune', year=1965, library_id=1, tenant_id=1)
    loan = Loan(id=42, status='issued')
    loan.book = book
    loan.user = user
    s = str(loan)
    assert 'Loan 42' in s
    assert 'Dune' in s
    assert 'paul' in s
    assert 'issued' in s
