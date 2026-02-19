import os
import pytest
from app import create_app, db
from app.models import User


@pytest.fixture
def app():
    """Create and configure a test app."""
    # Ensure the app factory picks up the in-memory SQLite DB for tests
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    app = create_app()
    app.config['TESTING'] = True
    # Keep as explicit override in case other code reads this value
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture
def admin_user(app):
    """Create an admin test user."""
    user = User(username='admin_test', email='admin@test.com', role='admin')
    user.set_password('password')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def regular_user(app):
    """Create a regular test user."""
    user = User(username='user_test', email='user@test.com', role='user')
    user.set_password('password')
    db.session.add(user)
    db.session.commit()
    return user
