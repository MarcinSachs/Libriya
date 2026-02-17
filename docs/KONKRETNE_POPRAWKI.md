# 🔧 Konkretne Poprawki - Kod do Implementacji

## 1. Wzmocnienie Rate Limiting

### Plik: `config.py`

Dodaj storage URL dla rate limiter (Redis):

```python
# Rate Limiting Configuration
RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')  # memory:// for dev, redis:// for prod
```

### Plik: `app/__init__.py`

Zaktualizuj konfigurację rate limitera:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=app.config.get('RATELIMIT_STORAGE_URL', 'memory://'),
    default_limits=["500 per day", "100 per hour"]
)
```

---

## 2. Dodaj Audit Logging na Wszystkie Wrażliwe Operacje

### Plik: `app/utils/audit_log.py` (rozszerz istniejący)

```python
def log_action(action_type, user_id, target_type, target_id, details=None, tenant_id=None):
    """
    Log all sensitive actions
    
    Args:
        action_type: 'create', 'update', 'delete', 'login', 'logout', 'toggle_feature'
        user_id: ID of user who performed action
        target_type: 'user', 'library', 'book', 'premium_feature', etc.
        target_id: ID of affected object
        details: Additional info (e.g., old value, new value)
        tenant_id: Tenant ID for isolation
    """
    from app.models import AuditLog
    from app import db
    import json
    from datetime import datetime
    
    audit_entry = AuditLog(
        action_type=action_type,
        user_id=user_id,
        target_type=target_type,
        target_id=target_id,
        details=json.dumps(details) if details else None,
        tenant_id=tenant_id,
        timestamp=datetime.utcnow()
    )
    db.session.add(audit_entry)
    db.session.commit()

# Upros Usage
from app.utils.audit_log import log_action

@bp.route('/users/delete/<int:user_id>', methods=['POST'])
def user_delete(user_id):
    user = User.query.get_or_404(user_id)
    
    # ... validation ...
    
    # Log before deletion
    log_action(
        action_type='delete',
        user_id=current_user.id,
        target_type='user',
        target_id=user_id,
        details={'username': user.username, 'email': user.email},
        tenant_id=current_user.tenant_id
    )
    
    db.session.delete(user)
    db.session.commit()
```

### Plik: `app/models.py` (dodaj nowy model)

```python
class AuditLog(db.Model):
    """Log of all sensitive actions for compliance and debugging"""
    id = db.Column(db.Integer, primary_key=True)
    action_type = db.Column(db.String(50), nullable=False, index=True)  # create, update, delete, toggle_feature
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    target_type = db.Column(db.String(50), nullable=False)  # 'user', 'library', 'book', 'premium_feature'
    target_id = db.Column(db.Integer)  # ID of affected object
    details = db.Column(db.JSON)  # Additional details (old_value, new_value, etc.)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), index=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6
    
    user = db.relationship('User', foreign_keys=[user_id])
    tenant = db.relationship('Tenant', foreign_keys=[tenant_id])
    
    @staticmethod
    def for_tenant(tenant_id):
        return AuditLog.query.filter_by(tenant_id=tenant_id).order_by(AuditLog.timestamp.desc())
    
    def __str__(self):
        return f"[{self.timestamp}] {self.user.username} {self.action_type} {self.target_type}#{self.target_id}"
```

---

## 3. Walidacja Subdomeny

### Plik: `app/forms.py`

```python
from wtforms.validators import Regexp, Length

class TenantForm(FlaskForm):
    name = StringField('Tenant Name', validators=[
        DataRequired(),
        Length(min=3, max=100)
    ])
    subdomain = StringField('Subdomain', validators=[
        DataRequired(),
        Regexp(
            '^[a-z0-9-]+$',
            message=_('Only lowercase letters, numbers and hyphens allowed')
        ),
        Length(min=3, max=20),
        # Custom validator for reserved subdomains
    ])
    
    def validate_subdomain(self, field):
        """Check for reserved subdomains and duplicates"""
        reserved = ['admin', 'www', 'mail', 'ftp', 'api', 'docs', 'support', 'test']
        if field.data.lower() in reserved:
            raise ValidationError(_('This subdomain is reserved'))
        
        # Check if already exists
        existing = Tenant.query.filter_by(subdomain=field.data.lower()).first()
        if existing:
            raise ValidationError(_('This subdomain is already taken'))
```

---

## 4. Email Verification System

### Plik: `app/models.py`

```python
class EmailVerificationToken(db.Model):
    """Email verification tokens"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    verified = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref='email_tokens')
    
    @classmethod
    def generate_token(cls, user_id, expires_in=3600):
        """Generate email verification token (valid for 1 hour by default)"""
        import secrets
        token = secrets.token_urlsafe(32)
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)
        
        entry = cls(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
        db.session.add(entry)
        db.session.commit()
        return token
    
    @classmethod
    def verify_token(cls, token):
        """Verify token and mark email as verified"""
        entry = cls.query.filter_by(token=token).first()
        
        if not entry:
            return None
        
        if datetime.datetime.utcnow() > entry.expires_at:
            return None
        
        entry.verified = True
        entry.user.email_verified = True
        db.session.commit()
        return entry.user
```

### Plik: `app/routes/auth.py`

```python
@bp.route('/verify-email/<token>')
def verify_email(token):
    """Verify email from link in email"""
    user = EmailVerificationToken.verify_token(token)
    
    if not user:
        flash(_('Invalid or expired verification link'), 'danger')
        return redirect(url_for('auth.login'))
    
    flash(_('Email verified successfully! You can now log in.'), 'success')
    return redirect(url_for('auth.login'))

# W funkcji register(), wysłij email z verification link
from flask_mail import Mail, Message

def send_verification_email(user, verification_url):
    """Send email verification link"""
    msg = Message(
        subject=_('Verify your email - Libriya'),
        recipients=[user.email],
        html=render_template('email/verify_email.html', 
                            user=user, 
                            verification_url=verification_url)
    )
    mail.send(msg)
```

---

## 5. Bezpieczeństwo Subdomeny

### Plik: `app/__init__.py`

```python
@app.before_request
def validate_subdomain():
    """Validate that subdomain exists"""
    from flask import abort
    
    host_parts = request.host.split(':')[0].split('.')
    
    # Jeśli jest subdomena (nie localhost, nie www)
    if len(host_parts) > 1 and host_parts[0] not in ('localhost', 'www'):
        subdomain = host_parts[0]
        tenant = Tenant.query.filter_by(subdomain=subdomain).first()
        
        if not tenant:
            # Subdomena nie istnieje
            abort(404)
```

---

## 6. Input Validation Helper

### Plik: `app/utils/validators.py` (nowy plik)

```python
import re
from wtforms.validators import ValidationError

def validate_username(username):
    """Validate username format"""
    if not re.match(r'^[a-zA-Z0-9_-]{3,20}$', username):
        raise ValidationError('Username must be 3-20 chars, alphanumeric with - and _')

def validate_email_format(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValidationError('Invalid email format')

def sanitize_string(text, max_length=None):
    """Remove potentially dangerous characters"""
    import html
    text = html.escape(text)
    if max_length:
        text = text[:max_length]
    return text
```

---

## 7. Error Handling Middleware

### Plik: `app/__init__.py`

```python
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('errors/404.html'), 404

@app.errorhandler(403)
def forbidden(error):
    """Handle 403 errors"""
    flash(_('You do not have permission to access this page'), 'danger')
    return render_template('errors/403.html'), 403

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    app.logger.error(f'Server error: {error}')
    return render_template('errors/500.html'), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded"""
    flash(_('Too many requests. Please try again later.'), 'danger')
    return redirect(request.referrer or url_for('main.home')), 429
```

---

## 8. CORS Configuration (jeśli API)

### Plik: `app/__init__.py`

```python
from flask_cors import CORS

def create_app(config_class=Config):
    app = Flask(__name__)
    
    # ... existing code ...
    
    # Configure CORS for API
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config.get('CORS_ORIGINS', ['http://localhost:3000']),
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
```

---

## 9. Logging Configuration

### Plik: `config.py`

```python
import logging
from logging.handlers import RotatingFileHandler
import os

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.path.join(BASE_DIR, 'logs/app.log')
LOG_MAX_BYTES = 10485760  # 10MB
LOG_BACKUP_COUNT = 10

def configure_logging(app):
    """Configure application logging"""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT
    )
    
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    
    file_handler.setLevel(getattr(logging, LOG_LEVEL))
    app.logger.addHandler(file_handler)
    app.logger.setLevel(getattr(logging, LOG_LEVEL))
    
    return app
```

### Plik: `libriya.py`

```python
from config import configure_logging

if __name__ == '__main__':
    app = create_app()
    configure_logging(app)
    app.run(host="0.0.0.0", port=5001, debug=debug_mode)
```

---

## 10. Database Backup Script

### Plik: `backup_db.py` (nowy plik)

```python
#!/usr/bin/env python
import os
import sqlite3
import shutil
from datetime import datetime

def backup_database():
    """Create backup of SQLite database"""
    db_path = 'instance/libriya.db'
    backup_dir = 'backups'
    
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f'{backup_dir}/libriya_backup_{timestamp}.db'
    
    if os.path.exists(db_path):
        shutil.copy2(db_path, backup_path)
        print(f'✅ Database backed up to {backup_path}')
    else:
        print(f'❌ Database not found at {db_path}')

if __name__ == '__main__':
    backup_database()
```

---

## Jak Implementować

### Priorytet Implementacji:

1. **Krok 1**: Audit Logging (test kritických operací)
2. **Krok 2**: Validacja Subdomeny (zabezpieczyć nowe tenanty)
3. **Krok 3**: Rate Limiting (zabezpieczyć endpoints)
4. **Krok 4**: Email Verification (dla produkcji)
5. **Krok 5**: Logging Configuration (monitoring)

### Przydatne Komendy:

```bash
# Uruchom Migration
flask db migrate -m "add_audit_log_and_email_verification"
flask db upgrade

# Testuj nowe funkcje
pytest tests/test_audit_log.py
pytest tests/test_subdomain_validation.py

# Sprawdź quality
pylint app/
flake8 app/
```

