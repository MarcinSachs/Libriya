# 🧪 Przygotowanie do Testów - Pytest

## Struktura katalogów testów

```
tests/
├── __init__.py
├── conftest.py              # Fixtures i konfiguracja
├── test_auth.py             # Testy autentykacji
├── test_models.py           # Testy modeli
├── test_routes.py           # Testy routów
├── test_premium.py          # Testy premium features
├── test_security.py         # Testy bezpieczeństwa
└── fixtures/
    ├── users.py
    └── data.py
```

---

## 1. Setup - `conftest.py`

```python
import pytest
import os
from app import create_app, db
from app.models import User, Tenant, Library
from config import Config

class TestConfig(Config):
    """Configuration for tests"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # In-memory database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'test-secret-key-do-not-use'
    WTF_CSRF_ENABLED = False  # Disable CSRF for testing

@pytest.fixture
def app():
    """Create application for the tests."""
    app = create_app(TestConfig)
    
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
    """A test runner for the app's CLI commands."""
    return app.test_cli_runner()

@pytest.fixture
def auth_client(client):
    """Client with authenticated user"""
    register_and_login(client)
    return client

def register_and_login(client, username='testuser', email='test@example.com', password='test123'):
    """Helper to register and login a user"""
    client.post(
        '/auth/register',
        data={
            'username': username,
            'email': email,
            'password': password,
            'password_confirm': password
        }
    )
    client.post(
        '/auth/login',
        data={
            'email_or_username': username,
            'password': password
        }
    )

@pytest.fixture
def super_admin(app):
    """Create a super-admin user"""
    with app.app_context():
        admin = User(
            username='superadmin',
            email='admin@example.com',
            role='admin',
            tenant_id=None
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        return admin

@pytest.fixture
def tenant(app):
    """Create a test tenant"""
    with app.app_context():
        t = Tenant(
            name='Test Tenant',
            subdomain='test-tenant'
        )
        db.session.add(t)
        db.session.commit()
        return t

@pytest.fixture
def tenant_admin(app, tenant):
    """Create a tenant-admin user"""
    with app.app_context():
        admin = User(
            username='tenantadmin',
            email='tadmin@example.com',
            role='admin',
            tenant_id=tenant.id
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        return admin
```

---

## 2. Testy Autentykacji - `test_auth.py`

```python
import pytest
from app.models import User

def test_login_with_valid_credentials(client, app):
    """Test login with valid email and password"""
    # Register user first
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        app.db.session.add(user)
        app.db.session.commit()
    
    # Login
    response = client.post(
        '/auth/login',
        data={'email_or_username': 'test@example.com', 'password': 'password123'},
        follow_redirects=True
    )
    
    assert response.status_code == 200
    assert b'Welcome' in response.data

def test_login_with_invalid_credentials(client):
    """Test login with invalid credentials"""
    response = client.post(
        '/auth/login',
        data={'email_or_username': 'nonexistent@example.com', 'password': 'wrong'},
        follow_redirects=True
    )
    
    assert response.status_code == 200
    assert b'Invalid' in response.data

def test_registration_creates_user(client, app):
    """Test that registration creates a new user"""
    response = client.post(
        '/auth/register',
        data={
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'password123',
            'password_confirm': 'password123'
        },
        follow_redirects=True
    )
    
    with app.app_context():
        user = User.query.filter_by(username='newuser').first()
        assert user is not None
        assert user.email == 'new@example.com'

def test_logout(auth_client):
    """Test logout functionality"""
    response = auth_client.get('/auth/logout', follow_redirects=True)
    assert response.status_code == 200

def test_rate_limiting_on_login(client):
    """Test rate limiting on login attempts"""
    for i in range(6):
        response = client.post(
            '/auth/login',
            data={'email_or_username': 'test@test.com', 'password': 'wrong'}
        )
    
    # 6th request should be rate limited
    assert response.status_code == 429
```

---

## 3. Testy Modeli - `test_models.py`

```python
import pytest
from app.models import User, Tenant, Library, Book

def test_user_password_hashing(app):
    """Test that passwords are properly hashed"""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('mysecretpassword')
        
        assert user.password_hash != 'mysecretpassword'
        assert user.check_password('mysecretpassword')
        assert not user.check_password('wrongpassword')

def test_super_admin_property():
    """Test super_admin property"""
    user1 = User(username='admin', role='admin', tenant_id=None)
    user2 = User(username='tadmin', role='admin', tenant_id=1)
    user3 = User(username='user', role='user', tenant_id=1)
    
    assert user1.is_super_admin is True
    assert user2.is_super_admin is False
    assert user3.is_super_admin is False

def test_tenant_admin_property():
    """Test tenant_admin property"""
    user1 = User(username='admin', role='admin', tenant_id=None)
    user2 = User(username='tadmin', role='admin', tenant_id=1)
    
    assert user1.is_tenant_admin is False
    assert user2.is_tenant_admin is True

def test_tenant_premium_features(app):
    """Test premium features on tenant"""
    with app.app_context():
        tenant = Tenant(
            name='Test',
            subdomain='test',
            premium_bookcover_enabled=True,
            premium_biblioteka_narodowa_enabled=False
        )
        
        features = tenant.get_enabled_premium_features()
        assert 'bookcover_api' in features
        assert 'biblioteka_narodowa' not in features
        assert tenant.is_premium_enabled('bookcover_api') is True
        assert tenant.is_premium_enabled('biblioteka_narodowa') is False

def test_user_for_tenant(app, tenant):
    """Test User.for_tenant() filter"""
    with app.app_context():
        user1 = User(username='user1', email='user1@test.com', tenant_id=tenant.id)
        user2 = User(username='user2', email='user2@test.com', tenant_id=tenant.id)
        user3 = User(username='user3', email='user3@test.com', tenant_id=999)
        
        db.session.add_all([user1, user2, user3])
        db.session.commit()
        
        tenant_users = User.for_tenant(tenant.id).all()
        assert len(tenant_users) == 2
        assert user3 not in tenant_users
```

---

## 4. Testy Routów - `test_routes.py`

```python
import pytest

def test_home_page_accessible(client):
    """Test home page is accessible"""
    response = client.get('/')
    assert response.status_code == 200

def test_admin_panel_requires_super_admin(client, auth_client, super_admin):
    """Test admin panel requires super-admin access"""
    response = client.get('/admin/tenants')
    assert response.status_code == 302  # Redirect to login
    
    # Login as super-admin
    client.post(
        '/auth/login',
        data={'email_or_username': 'superadmin', 'password': 'admin123'}
    )
    response = client.get('/admin/tenants')
    assert response.status_code == 200

def test_super_admin_cannot_access_tenant_pages(auth_client):
    """Test super-admin gets 403 when accessing tenant pages"""
    response = auth_client.get('/books')
    assert response.status_code == 403

def test_tenant_users_cannot_access_admin(auth_client, tenant_admin):
    """Test tenant users cannot access super-admin pages"""
    response = auth_client.get('/admin/tenants')
    assert response.status_code == 403

def test_create_library(auth_client, app):
    """Test creating a library"""
    response = auth_client.post(
        '/libraries/add',
        data={'name': 'My Library'},
        follow_redirects=True
    )
    
    assert response.status_code == 200
    with app.app_context():
        lib = Library.query.filter_by(name='My Library').first()
        assert lib is not None
```

---

## 5. Testy Bezpieczeństwa - `test_security.py`

```python
import pytest

def test_csrf_protection(client, app):
    """Test CSRF protection is enabled in production"""
    # This test checks that forms require CSRF tokens
    response = client.get('/admin/tenants/add')
    assert b'csrf_token' in response.data

def test_sql_injection_protection(client):
    """Test SQL injection is prevented"""
    malicious_input = "admin' OR '1'='1"
    response = client.post(
        '/auth/login',
        data={'email_or_username': malicious_input, 'password': 'test'},
        follow_redirects=True
    )
    
    # Should not return error about SQL, just invalid credentials
    assert response.status_code == 200

def test_xss_protection(client, app):
    """Test XSS protection"""
    with app.app_context():
        user = User(
            username='test',
            email='test@test.com',
            tenant_id=None
        )
        user.set_password('test')
        db.session.add(user)
        db.session.commit()
    
    # Try to inject script
    response = client.post(
        '/auth/login',
        data={
            'email_or_username': '<script>alert("xss")</script>',
            'password': 'test'
        }
    )
    
    # Script should be escaped
    assert b'<script>' not in response.data

def test_password_reset_rate_limited(client):
    """Test password reset is rate limited"""
    for i in range(4):
        client.post(
            '/auth/password-reset',
            data={'email': 'test@test.com'}
        )
    
    # 4th request should be rate limited
    response = client.post(
        '/auth/password-reset',
        data={'email': 'test@test.com'}
    )
    assert response.status_code == 429

def test_tenant_isolation(client, app, tenant):
    """Test that users cannot access other tenants' data"""
    with app.app_context():
        user1 = User(
            username='user1',
            email='user1@test.com',
            tenant_id=tenant.id
        )
        user1.set_password('pass')
        db.session.add(user1)
        
        tenant2 = Tenant(name='Tenant2', subdomain='tenant2')
        db.session.add(tenant2)
        db.session.commit()
    
    # Login as user1
    client.post(
        '/auth/login',
        data={'email_or_username': 'user1', 'password': 'pass'},
        follow_redirects=True
    )
    
    # Try to access tenant2's data (via subdomain)
    response = client.get(
        'http://tenant2.localhost/books',
        follow_redirects=True
    )
    
    # Should be denied
    assert response.status_code == 403
```

---

## 6. Testy Premium Features - `test_premium.py`

```python
import pytest

def test_premium_feature_toggle(client, app, super_admin):
    """Test toggling premium features"""
    with app.app_context():
        tenant = Tenant(name='Test', subdomain='test')
        db.session.add(tenant)
        db.session.commit()
        tenant_id = tenant.id
    
    # Login as super-admin
    client.post(
        '/auth/login',
        data={'email_or_username': 'superadmin', 'password': 'admin123'}
    )
    
    # Toggle feature
    response = client.post(
        f'/admin/tenants/{tenant_id}/premium/bookcover_api/toggle',
        json={}
    )
    
    assert response.status_code == 200
    
    with app.app_context():
        tenant = Tenant.query.get(tenant_id)
        assert tenant.premium_bookcover_enabled is True

def test_premium_context_initialization(app, tenant_admin):
    """Test PremiumContext is initialized correctly"""
    with app.app_context():
        from app.services.premium.context import PremiumContext
        
        tenant = tenant_admin.tenant
        tenant.premium_bookcover_enabled = True
        db.session.commit()
        
        enabled = tenant.get_enabled_premium_features()
        PremiumContext.set_for_tenant(tenant.id, set(enabled))
        
        assert PremiumContext.is_enabled('bookcover_api') is True
```

---

## Jak Uruchomić Testy

```bash
# Zainstaluj pytest
pip install pytest pytest-cov

# Uruchom wszystkie testy
pytest

# Uruchom z raportowaniem pokrycia kodu
pytest --cov=app --cov-report=html

# Uruchom konkretny test
pytest tests/test_auth.py::test_login_with_valid_credentials

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Show print statements
pytest -s
```

---

## Coverage Goals

- **Overall Coverage**: Minimum 80%
- **Critical Code** (auth, security): 95%+
- **Models**: 90%+
- **Routes**: 85%+

Sprawdź raport:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

