import pytest
from app.forms import BookForm, UserForm
from flask import Flask
from unittest.mock import patch
from flask_babel import Babel
from werkzeug.datastructures import MultiDict  # Added import

class DummyGenre:
    def __init__(self, id, name):
        self.id = id
        self.name = name

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['WTF_I18N_ENABLED'] = False
    # Add Babel for tests
    babel = Babel(app)
    app.config['BABEL_DEFAULT_LOCALE'] = 'en'
    return app

def test_book_form_valid():
    app = create_app()
    with app.app_context():
        from unittest.mock import patch
        class DummyGenre:
            def __init__(self, id, name):
                self.id = id
                self.name = name
        with patch('app.forms.Genre.query') as mock_genre_query:
            mock_genre_query.all.return_value = [DummyGenre(1, 'Fiction')]
            form = BookForm(formdata=MultiDict({  # Use formdata
                'isbn': '9780545003957',
                'title': 'Test Book',
                'author': 'Author',
                'library': 1,
                'genres': [1],
                'year': 2020
            }))
            form.library.choices = [(1, 'Test Library')]
            assert form.validate()

def test_book_form_invalid_isbn():
    app = create_app()
    with app.app_context():
        from unittest.mock import patch
        class DummyGenre:
            def __init__(self, id, name):
                self.id = id
                self.name = name
        with patch('app.forms.Genre.query') as mock_genre_query:
            mock_genre_query.all.return_value = [DummyGenre(1, 'Fiction')]
            form = BookForm(formdata=MultiDict({  # Use formdata
                'isbn': 'badisbn',
                'title': 'Test Book',
                'author': 'Author',
                'library': 1,
                'genres': [1],
                'year': 2020
            }))
            form.library.choices = [(1, 'Test Library')]
            valid = form.validate()
            if valid:
                print('Form should not be valid, errors:', form.errors)
            assert not valid
            assert 'isbn' in form.errors

def test_user_form_valid():
    app = create_app()
    with app.app_context():
        form = UserForm(data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'StrongPass123!',
            'confirm_password': 'StrongPass123!'
        })
        assert form.validate()

def test_user_form_invalid_email():
    app = create_app()
    with app.app_context():
        form = UserForm(data={
            'username': 'testuser',
            'email': 'not-an-email',
            'password': 'StrongPass123!',
            'confirm_password': 'StrongPass123!'
        })
        assert not form.validate()
        assert 'email' in form.errors
