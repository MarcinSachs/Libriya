# 🔐 Security Checklist - OWASP Top 10

## ✅ Pre-Production Security Audit

### 1. Injection Attacks (SQL, NoSQL, OS)

- [x] **SQL Injection**: SQLAlchemy ORM chroni przed parametryzowanymi queryami
  - ✅ Używane parameterized queries wszędzie
  - ⚠️ Nie znaleziono raw SQL queries - DOBRZE
  
- [x] **Input Validation**: Dodaj validators na wszystkie formularze
  - [x] Username: `^[a-zA-Z0-9_-]{3,20}$`
  - [x] Email: RFC 5322 format
  - [x] Subdomain: `^[a-z0-9-]{3,20}$`
  
- [ ] **Output Encoding**: Sprawdź czy Jinja2 auto-escapes
  - ✅ Jinja2 ma auto-escape domyślnie (nie dodawaj `|safe` bez powodu)
  - [ ] Review templates dla `|safe` filters

````markdown
# 🔐 Security Checklist - OWASP Top 10

## ✅ Pre-Production Security Audit (status updated)

### 1. Injection Attacks (SQL, NoSQL, OS)

- [x] **SQL Injection**: SQLAlchemy ORM chroni przed parametryzowanymi queryami
  - ✅ Używane parameterized queries wszędzie
  - ⚠️ Nie znaleziono raw SQL queries - DOBRZE
  
- [x] **Input Validation**: Częściowo wdrożone
  - ✅ Username + Email validators i `sanitize_string` dodane i podłączone do głównych formularzy
  - ✅ Subdomain validator (`^[a-z0-9-]{3,20}$`)
  
- [x] **Output Encoding**: Sprawdzone
  - ✅ Jinja2 auto-escape domyślnie (nie używać `|safe` bez potrzeby)

---

### 2. Broken Authentication

- [x] **Password Requirements** — Partially implemented
  - [x] Minimum 12 characters enforced (`validate_password_field`)
  - [x] Mix of uppercase, lowercase, numbers, special chars enforced
  - [ ] No common passwords (haveibeenpwned) — optional
    - Behavior: HIBP checks are disabled outside production. When `APP_ENV` (or `FLASK_ENV`) is `production`, HIBP will be enabled by default unless `ENABLE_PWNED_CHECK` is explicitly set in the environment.
    - To enable in production explicitly, set in your `.env`:

      ```text
      APP_ENV=production
      ENABLE_PWNED_CHECK=True  # optional; prod enables by default if not set
      HIBP_TIMEOUT=5.0
      HIBP_CACHE_TTL=86400
      ```
    - Uses k-anonymity (only SHA1 prefix sent); requires outbound network access and a caching layer (recommended) to avoid rate limits.

```python
# app/utils/password_validator.py (proposal exists in docs; not implemented)
```

- [x] **Session Management**
  - ✅ `flask-login` użyty
  - ✅ Session timeout skonfigurowany (zgodnie z wcześniejszymi zmianami)
  
- [ ] **Multi-Factor Authentication (MFA)** — PENDING
  - [ ] Add TOTP (Time-based One-Time Password) support
  - [ ] Email-based MFA as fallback

- [x] **Password Hashing**
  - ✅ `werkzeug.security.generate_password_hash` (PBKDF2) używane
  - ⚠️ Rozważ upgrade do Argon2 — PENDING

- [x] **Rate Limiting** (Partial)
  - ✅ Login rate limiting in place (5/min)
  - ⚠️ Limiter używa in-memory store w konfiguracji (nieprodukcyjne) — PENDING: production backend (Redis)
  - [ ] Password reset rate limiting — PENDING

---

### 3. Sensitive Data Exposure

- [ ] **HTTPS/TLS** — PENDING
  - [ ] Wszystkie production URLs muszą być HTTPS
  - [ ] Redirect HTTP → HTTPS — PENDING
  - [x] HSTS header obecny w `set_security_headers` (częściowo wdrożone)

- [ ] **Database Encryption** — PENDING
  - [ ] Encrypt sensitive fields (SSN, billing info)
  - [ ] Connection encryption (SSL/TLS) — PENDING (depends on DATABASE_URL)

- [ ] **API Keys / Secrets** — PENDING (use vaults / env secrets)

- [x] **Data Backups** — Partial
  - ✅ `manage_db.py backup` added: supports SQLite file copy and `mysqldump` for MySQL/MariaDB
  - [ ] Automatyczne harmonogramy/backups (cron/CI) — PENDING
  - [ ] Szyfrowanie backupów w spoczynku i transfer — PENDING

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
  - ✅ `@role_required` decorator present
  
- [x] **Multi-Tenant Isolation**
  - ✅ `verify_tenant_access()` middleware present
  - ✅ Subdomain-based routing
  - ⚠️ Pełny audit zapytań pod kątem `tenant_id` — PENDING (manual audit required)

Checklist (manual audit needed):
- [ ] `Book.query.filter_by(tenant_id=current_user.tenant_id)` WSZĘDZIE — PENDING
- [ ] `Loan.query.filter_by(tenant_id=current_user.tenant_id)` WSZĘDZIE — PENDING
- [ ] Library queries filtrowane po tenant — PENDING
- [ ] User queries filtrowane po tenant — PENDING

---

### 6. Security Misconfiguration

- [ ] **Environment Variables / SECRET_KEY** — PENDING
  - [ ] Ensure `SECRET_KEY` not checked into repo; generate strong key for production

- [x] **Debug Mode**
  - ✅ `DEBUG=False` expected in production; code respects config
  - ⚠️ Ensure `FLASK_ENV=production` in deployment

- [ ] **Dependencies / Pinning / Scanning** — PENDING
  - [ ] Add `pip-audit`/CI scanning
  - [ ] Pin critical versions in `requirements.txt`

- [x] **Error Pages / Error Handling**
  - ✅ Custom error handlers added (`404`, `403`, `500`, `429`) in `app/__init__.py`

---

### 7. Cross-Site Scripting (XSS)

- [x] **Output Encoding**
  - ✅ Jinja2 auto-escape enabled
  
- [x] **CSRF Protection**
  - ✅ `flask-wtf` CSRF tokens and `CSRFProtect` initialized
  
- [ ] **Content Security Policy (CSP)** — Partial
  - ✅ CSP header present in `app/__init__.py`
  - ⚠️ CSP uses `'unsafe-inline'` in places — recommend moving to `nonce`-based approach — PENDING

- [ ] **HTTPOnly / Secure / SameSite Cookies** — PENDING
  - Suggest adding to `config.py`:
    ```python
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    ```

---

### 8. Cross-Site Request Forgery (CSRF)

- [x] **CSRF Tokens**
  - ✅ All forms have `csrf_token` via `flask-wtf`
  
- [ ] **SameSite Cookie** — PENDING (see cookie settings above)

---

### 9. Using Components with Known Vulnerabilities

- [ ] **Dependency Scanning / CI** — PENDING
  - Recommend adding `pip-audit` and Dependabot or similar

- [ ] **Version Pinning** — PENDING (requirements.txt currently uses ranges)

---

### 10. Insufficient Logging & Monitoring

- [x] **Audit Logging** — Partial
  - ✅ `app/utils/audit_log.py` writes per-tenant JSON-lines
  - ✅ `AuditLogFile` model exists and is updated by logger
  - [ ] Include user-agent in logs / store IP+UA consistently — PENDING
  - [ ] Retention/archival automation / centralization — PENDING

- [ ] **Security Monitoring / Alerts** — PENDING
  - Brute force detection, alerting, and central aggregation not yet in place

- [ ] **Log Aggregation** — PENDING
  - Recommend centralizing logs (ELK / CloudWatch) and adding retention policies

---

## 🚀 Production Deployment Checklist (high-level)

```
SECURITY CONFIGURATION
  [ ] SECRET_KEY changed to random value (PENDING)
  [ ] DEBUG = False
  [ ] TESTING = False
  [ ] FLASK_ENV = production
  [ ] SQLALCHEMY_ECHO = False

HTTPS/TLS
  [ ] SSL certificate installed
  [ ] HTTPS enforced (redirect HTTP → HTTPS) (PENDING)
  [x] HSTS header enabled (present in `app/__init__.py`)

DATABASE
  [x] Database backup command added (`manage_db.py backup`) — manual/restore testing and encryption: PENDING
  [ ] Connection encrypted (SSL)
  [ ] Database user has limited privileges
  [ ] Backups encrypted at rest

API SECURITY
  [x] Rate limiting enabled (login)
  [ ] Input validation on all endpoints — PENDING (some validators implemented)
  [ ] Output encoding correct
  [ ] CORS configured properly (not *.allow-all)

AUTHENTICATION
  [ ] Password requirements enforced (12+ chars) — PENDING
  [x] Session timeout configured
  [ ] MFA optional or required — PENDING
  [x] Brute force protection (rate limiting) partially in place

MONITORING
  [ ] Audit logging enabled centrally — PARTIAL
  [ ] Error tracking (Sentry) — PENDING
  [ ] Performance monitoring (New Relic, DataDog) — PENDING
  [ ] Security scanning enabled (OWASP ZAP) — PENDING

MAINTENANCE
  [ ] Dependency updates scheduled
  [ ] Security patches process documented
  [ ] Incident response plan created
  [ ] Backup & disaster recovery tested
 ```

---

## 🧪 Security Testing Tools (recommendations)

```bash
# 1. Static Analysis
pip install pylint bandit
bandit -r app/

# 2. Dependency Scanning
pip install pip-audit
pip-audit

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

- **Security Issues**: Utwórz proces dla security@yourcompany.com
- **Responsible Disclosure**: Allow 90 days before public disclosure
- **Bug Bounty**: Rozważ program (HackerOne, Bugcrowd)

---

## 📚 References

- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org/)
- [Flask Security](https://flask-security-too.readthedocs.io/)
- [NIST Password Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html)

````
  [ ] Database user has limited privileges

  [ ] Backups encrypted at rest
