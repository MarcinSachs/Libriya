# 🔐 Security Checklist - OWASP Top 10

## ✅ Pre-Production Security Audit

### 1. Injection Attacks (SQL, NoSQL, OS)

- [x] **SQL Injection**: SQLAlchemy ORM chroni przed parametryzowanymi queryami
  - ✅ Używane parameterized queries wszędzie
  - ⚠️ Nie znaleziono raw SQL queries - DOBRZE
  
- [ ] **Input Validation**: Dodaj validators na wszystkie formularze
  - [ ] Username: `^[a-zA-Z0-9_-]{3,20}$`
  - [ ] Email: RFC 5322 format
  - [ ] Subdomain: `^[a-z0-9-]{3,20}$`
  
- [ ] **Output Encoding**: Sprawdź czy Jinja2 auto-escapes
  - ✅ Jinja2 ma auto-escape domyślnie (nie dodawaj `|safe` bez powodu)
  - [ ] Review templates dla `|safe` filters

**Kod**: Patrz `KONKRETNE_POPRAWKI.md` → Sekcja 6

---

### 2. Broken Authentication

- [ ] **Password Requirements**
  - [ ] Minimum 12 characters (NIST guidelines)
  - [ ] Mix of uppercase, lowercase, numbers, special chars
  - [ ] No common passwords (check against haveibeenpwned)

```python
# app/utils/password_validator.py
import re
import requests

def validate_password_strength(password):
    """Validate password meets security requirements"""
    if len(password) < 12:
        raise ValueError('Password must be at least 12 characters')
    
    if not re.search(r'[A-Z]', password):
        raise ValueError('Password must contain uppercase letter')
    
    if not re.search(r'[a-z]', password):
        raise ValueError('Password must contain lowercase letter')
    
    if not re.search(r'[0-9]', password):
        raise ValueError('Password must contain number')
    
    # Check against common passwords
    # response = requests.post('https://haveibeenpwned.com/api/v3/range/...')
```

- [x] **Session Management**
  - ✅ Flask-Login used
  - ✅ Session timeout configured
  
- [ ] **Multi-Factor Authentication (MFA)**
  - [ ] Add TOTP (Time-based One-Time Password) support
  - [ ] Email-based MFA as fallback

- [x] **Password Hashing**
  - ✅ werkzeug.security.generate_password_hash (PBKDF2)
  - ⚠️ Rozważ upgrade do Argon2

```bash
pip install argon2-cffi
```

- [x] **Rate Limiting**
  - ✅ 5 per minute na login (jest)
  - [ ] Dodaj na password reset (3 per hour)

---

### 3. Sensitive Data Exposure

- [ ] **HTTPS/TLS**
  - [ ] Wszystkie production URLs muszą być HTTPS
  - [ ] Redirect HTTP → HTTPS
  - [ ] HSTS header (już jest w `set_security_headers`)

```python
# .env
FORCE_HTTPS=true
```

- [ ] **Database Encryption**
  - [ ] Encrypt sensitive fields (SSN, billing info)
  - [ ] Connection encryption (SSL/TLS)

```python
DATABASE_URL=mysql+pymysql://user:pass@host/db?ssl=true
```

- [ ] **API Keys**
  - [ ] Brak API keys w .env (potrzebne env secrets)
  - [ ] Rotate keys regularly
  - [ ] Store in secure vault (AWS Secrets Manager, HashiCorp Vault)

- [x] **Data Backups**
  - [ ] Implement automated backups (patrz `backup_db.py`)
  - [ ] Test restore procedures regularly
  - [ ] Backups encrypted in transit and at rest

---

### 4. XML External Entities (XXE)

- ✅ **XML Parsing**: Aplikacja nie używa XML - brak ryzyka
- [ ] **File Upload**: Jeśli dodać upload książek/covers:
  - Waliduj file types
  - Limit file sizes
  - Skanuj na malware (ClamAV)

---

### 5. Broken Access Control

- [x] **Role-Based Access Control (RBAC)**
  - ✅ admin, manager, user roles
  - ✅ @role_required decorator
  
- [x] **Multi-Tenant Isolation**
  - ✅ verify_tenant_access() middleware
  - ✅ Subdomain-based routing
  - ⚠️ Sprawdzić wszystkie queries czy mają `tenant_id` filter

Checklist:
- [ ] `Book.query.filter_by(tenant_id=current_user.tenant_id)` WSZĘDZIE
- [ ] `Loan.query.filter_by(tenant_id=current_user.tenant_id)` WSZĘDZIE
- [ ] Library queries filtrowane po tenant
- [ ] User queries filtrowane po tenant

---

### 6. Security Misconfiguration

- [ ] **Environment Variables**
  - [ ] SECRET_KEY nie może być "your-secret-key-here"
  - [ ] Generate na production: `python -c "import secrets; print(secrets.token_hex(32))"`
  - [ ] Store w `.env` (nie w repozytorium!)

```bash
# Generate strong SECRET_KEY
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
```

- [ ] **Debug Mode**
  - ✅ DEBUG=False w .env (jest)
  - ⚠️ Ale FLASK_ENV=production musi być set

```python
# config.py
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
if DEBUG:
    print("⚠️ DEBUG MODE ENABLED - UNSAFE FOR PRODUCTION")
```

- [ ] **Dependencies**
  - [ ] Regular `pip list --outdated` checks
  - [ ] Use `safety` lub `pip-audit` do scanowania

```bash
pip install safety
safety check

# Lub
pip install pip-audit
pip-audit
```

- [ ] **Error Messages**
  - [ ] Nie ujawniaj stack traces użytkownikom
  - [ ] Use custom error pages (już są w app/__init__.py)

---

### 7. Cross-Site Scripting (XSS)

- [x] **Output Encoding**
  - ✅ Jinja2 auto-escape enabled
  
- [x] **CSRF Protection**
  - ✅ flask-wtf CSRF tokens
  
- [ ] **Content Security Policy (CSP)**
  - ✅ CSP header jest już (patrz app/__init__.py)
  - [ ] Review CSP na 'unsafe-inline' (powinno być 'nonce' zamiast)

```python
# Wzmocnić CSP - zamiast 'unsafe-inline' użyj nonce
# (wymaga generowania nonce na każdy request)
```

- [ ] **HTTPOnly Cookies**
  - [ ] Set session cookie as HTTPOnly

```python
# config.py
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'Lax'
```

---

### 8. Cross-Site Request Forgery (CSRF)

- [x] **CSRF Tokens**
  - ✅ All forms have csrf_token
  - ✅ flask-wtf validation
  
- [ ] **SameSite Cookie**
  - [ ] Set SameSite=Lax/Strict na session cookies

```python
# config.py
SESSION_COOKIE_SAMESITE = 'Lax'  # lub 'Strict'
```

---

### 9. Using Components with Known Vulnerabilities

- [ ] **Dependency Scanning**
  - [ ] Setup continuous scanning (GitHub Dependabot, Snyk)
  - [ ] Regular updates

```bash
# Weekly checks
pip list --outdated
pip install --upgrade flask flask-sqlalchemy ...
```

- [ ] **Version Pinning**
  - [ ] Pin versions w requirements.txt

```
flask==3.0.0
flask-sqlalchemy==3.1.0
```

---

### 10. Insufficient Logging & Monitoring

- [ ] **Audit Logging**
  - [ ] Implement AuditLog model (patrz KONKRETNE_POPRAWKI.md)
  - [ ] Log: logins, role changes, data modifications
  - [ ] Store IP address i user agent

- [ ] **Security Monitoring**
  - [ ] Monitor for brute force attempts
  - [ ] Alert on failed logins
  - [ ] Track premium feature changes

- [ ] **Log Aggregation**
  - [ ] Centralize logs (ELK, Splunk, CloudWatch)
  - [ ] Set retention policies (90 days minimum)

---

## 🚀 Production Deployment Checklist

```
SECURITY CONFIGURATION
  [ ] SECRET_KEY changed to random value
  [ ] DEBUG = False
  [ ] TESTING = False
  [ ] FLASK_ENV = production
  [ ] SQLALCHEMY_ECHO = False

HTTPS/TLS
  [ ] SSL certificate installed
  [ ] HTTPS enforced (redirect HTTP → HTTPS)
  [ ] HSTS header enabled
  [ ] Certificate pinning (if needed)

DATABASE
  [ ] Database backed up
  [ ] Backup tested (restore procedure works)
  [ ] Connection encrypted (SSL)
  [ ] Database user has limited privileges
  [ ] Backups encrypted at rest

API SECURITY
  [ ] Rate limiting enabled
  [ ] Input validation on all endpoints
  [ ] Output encoding correct
  [ ] CORS configured properly (not *.allow-all)

AUTHENTICATION
  [ ] Password requirements enforced (12+ chars)
  [ ] Session timeout configured (15 min)
  [ ] MFA optional or required
  [ ] Brute force protection active

MONITORING
  [ ] Audit logging enabled
  [ ] Error tracking (Sentry)
  [ ] Performance monitoring (New Relic, DataDog)
  [ ] Security scanning enabled (OWASP ZAP)

MAINTENANCE
  [ ] Dependency updates scheduled
  [ ] Security patches process documented
  [ ] Incident response plan created
  [ ] Backup & disaster recovery tested
```

---

## 🧪 Security Testing Tools

```bash
# 1. Static Analysis
pip install pylint bandit
bandit -r app/

# 2. Dependency Scanning
pip install safety
safety check

# 3. OWASP ZAP (Dynamic Analysis)
# Download from: https://www.zaproxy.org/
# Run against staging environment

# 4. SSL Testing
# Use: https://www.ssllabs.com/ssltest/

# 5. NIST Password Checker
# Run locally or use API
```

---

## 📞 Security Contacts

- **Security Issues**: Utwórz process dla security@yourcompany.com
- **Responsible Disclosure**: Allow 90 days before public disclosure
- **Bug Bounty**: Rozważ program (HackerOne, Bugcrowd)

---

## 📚 References

- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org/)
- [Flask Security](https://flask-security-too.readthedocs.io/)
- [NIST Password Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html)

