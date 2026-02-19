# 📊 Analiza Kodu - Raport Pre-Produkcyjny

**Data**: 2026-02-19  
**Status**: ⚠️ **KRYTYCZNE PROBLEMY ZNALEZIONE**

---

## 🎯 Streszczenie Wykonawcze

Aplikacja **Libriya** jest dobrze zbudowana architektonicznie, ale wymaga **finalnych poprawek bezpieczeństwa i stabilności** przed produkcją. Znaleziono:

- ✅ **13 obszarów w dobrej kondycji**
- ⚠️ **9 problemów do naprawy**
- 🔴 **3 KRYTYCZNE problemy wymagające natychmiastowego działania**

---

## 🔴 KRYTYCZNE PROBLEMY

### 1. **SECRET_KEY nie jest skonfigurowany**

**Lokalizacja**: `config.py`, linia 14  
**Ważność**: 🔴 KRYTYCZNA  
**Problem**: `SECRET_KEY` jest wymagane (bez wartości domyślnej) i musi być ustawione w `.env`

```python
# config.py
SECRET_KEY: str  # ← Brak wartości domyślnej!
```

**Zagrożenie**:
- Aplikacja nie uruchomi się bez `SECRET_KEY`
- Jeśli ktoś wstawi słabą wartość, wszystkie sesje i tokeny CSRF są zagrożone

**Rozwiązanie**:
```bash
# Wygeneruj silny klucz
python -c "import secrets; print(secrets.token_hex(32))"
# Dodaj do .env
SECRET_KEY=<wygenerowana_wartość>
```

**Status**: ⏳ WYMAGA AKCJI

---

### 2. **CSP używa `unsafe-inline` - narażenie na XSS**

**Lokalizacja**: `app/__init__.py`, linie 193-197  
**Ważność**: 🔴 KRYTYCZNA (XSS)

```python
# ❌ NIEBEZPIECZNE
response.headers['Content-Security-Policy'] = (
    "default-src 'self'; script-src 'self' 'unsafe-inline' "  # ← TO JEST PROBLEM!
    "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com..."
)
```

**Zagrożenie**:
- `unsafe-inline` pozwala na inline JavaScript/CSS
- Atakujący mogą wstrzyknąć złośliwy skrypt jeśli będzie XSS
- Neguje wartość CSP

**Rozwiązanie** (krótkoterminowe):
```python
# Dodaj nonce do Jinja2
def inject_nonce():
    import secrets
    return secrets.token_hex(16)

# W szablonach
<script nonce="{{ nonce }}">...</script>
<style nonce="{{ nonce }}">...</style>

# CSP w aplikacji
"script-src 'nonce-{{ nonce }}' https://cdn.tailwindcss.com"
```

**Status**: ⏳ WYMAGA AKCJI

---

### 3. **Rate limiting używa in-memory store (nieprodukcyjne)**

**Lokalizacja**: `app/__init__.py`, linia 19  
**Ważność**: 🔴 KRYTYCZNA (DDoS/Brute Force)

```python
# ❌ NIEBEZPIECZNE
limiter = Limiter(key_func=get_remote_address)
# Brak konfiguracji storage backend!
```

**Zagrożenie**:
- W środowisku multi-worker, każdy process ma własny limit
- Atakujący mogą obejść limit rozdzielając zaproszenia między procesy
- Przy restartach limity resetują się

**Rozwiązanie** (wymaga Redisa):
```bash
pip install redis
```

```python
# config.py
RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/1')

# app/__init__.py
from flask_limiter.util import get_remote_address
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=app.config.get('RATELIMIT_STORAGE_URL')
)
```

**Status**: ⏳ WYMAGA REDISA LUB MEMCACHED

---

## ⚠️ POWAŻNE PROBLEMY

### 4. **Brak HTTPS redirect**

**Lokalizacja**: Nie zaimplementowana  
**Ważność**: ⚠️ POWAŻNA

**Zagrożenie**:
- Użytkownicy mogą się logować przez HTTP
- Kredencjale mogą być przechwycone

**Rozwiązanie**:
```python
# app/__init__.py
@app.before_request
def enforce_https():
    if not app.debug and not request.is_secure and request.headers.get('X-Forwarded-Proto', 'http') == 'http':
        return redirect(request.url.replace('http://', 'https://'), code=301)
```

**Status**: ⏳ WYMAGA KONFIGURACJI SERWERA

---

### 5. **Brak cookie security flags**

**Lokalizacja**: `config.py` (nie zaimplementowane)  
**Ważność**: ⚠️ POWAŻNA

```python
# ❌ Brak tej konfiguracji
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'Lax'
```

**Zagrożenie**:
- JavaScript może stolen session cookies
- CSRF ataki mogą być wykonywane

**Rozwiązanie**:
```python
# config.py - dodaj do Config class
SESSION_COOKIE_HTTPONLY: bool = True
SESSION_COOKIE_SECURE: bool = True  # True w production
SESSION_COOKIE_SAMESITE: str = 'Lax'
PERMANENT_SESSION_LIFETIME: int = 3600  # 1 hour
```

**Status**: ⏳ WYMAGA DODANIA

---

### 6. **Password reset rate limiting brakuje**

**Lokalizacja**: `app/routes/auth.py` (brakuje implementacji)  
**Ważność**: ⚠️ POWAŻNA

**Zagrożenie**:
- Atakujący mogą brute-force tokeny reset
- Enumeration emaili poprzez flood

**Rozwiązanie**:
```python
# app/routes/auth.py
@bp.route("/forgot-password", methods=['POST'])
@limiter.limit("3 per hour")  # ← DODAJ TO!
def forgot_password():
    # ... implementacja
```

**Status**: ⏳ WYMAGA DODANIA

---

### 7. **Brak Argon2 - słaba hash function**

**Lokalizacja**: `app/models.py`, `app/routes/auth.py`  
**Ważność**: ⚠️ POWAŻNA

**Problem**: Aplikacja używa PBKDF2 (Werkzeug default)

```python
# ❌ PBKDF2 (słabsze)
from werkzeug.security import generate_password_hash

# ✅ Powinno być Argon2
from argon2 import PasswordHasher
```

**Zagrożenie**:
- PBKDF2 jest dużo szybsza do brute-force
- Argon2 ma memory hardening

**Rozwiązanie**:
```bash
pip install argon2-cffi
```

```python
# app/utils/password_handler.py (nowy plik)
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher()

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(password: str, hash: str) -> bool:
    try:
        ph.verify(hash, password)
        return True
    except VerifyMismatchError:
        return False
```

**Status**: ⏳ WYMAGA MIGRACJI

---

### 8. **Brak sprawdzenia pod kątem zwykłych haseł**

**Lokalizacja**: `app/utils/password_validator.py` (częściowo zaimplementowane)  
**Ważność**: ⚠️ POWAŻNA

**Problem**: HIBP check jest opcjonalny i może nie działać

```python
# app/utils/password_validator.py
if enable_pwned:
    try:
        count = check_pwned_password(password)
    except Exception:
        # Network failures shouldn't block registration
        count = 0  # ← TO JEST PROBLEM!
```

**Zagrożenie**:
- Jeśli network nie działa, ANY hasło jest akceptowane
- Powinna być cached lista top 1000 haseł

**Rozwiązanie**:
```python
# Zamiast polega na HIBP, sprawdzaj top 10000 haseł offline
# Dostępne: https://github.com/danielmiessler/SecLists/

TOP_PASSWORDS = set()  # Załaduj z pliku

def is_password_too_common(password: str) -> bool:
    return password.lower() in TOP_PASSWORDS
```

**Status**: ⏳ WYMAGA POPRAWY

---

### 9. **Brak walidacji file upload'ów**

**Lokalizacja**: `app/routes/books.py` (upload covers)  
**Ważność**: ⚠️ POWAŻNA

**Zagrożenie**:
- Brak antyvirus check
- Brak path traversal protection
- Brak MIME type validation

**Rozwiązanie**:
```bash
pip install python-magic python-magic-bin
```

```python
# app/utils/file_validator.py
import magic
import os

ALLOWED_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def validate_book_cover(file):
    # Check extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Invalid extension: {ext}")
    
    # Check file size
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    if size > MAX_FILE_SIZE:
        raise ValueError(f"File too large: {size}")
    
    # Check MIME type
    file.seek(0)
    mime = magic.from_buffer(file.read(512), mime=True)
    if mime not in ALLOWED_TYPES:
        raise ValueError(f"Invalid MIME type: {mime}")
    
    file.seek(0)
    return True
```

**Status**: ⏳ WYMAGA IMPLEMENTACJI

---

## 🟡 ŚREDNIE PROBLEMY

### 10. **Brak database encryption**

**Lokalizacja**: `config.py`, setup MySQL  
**Ważność**: 🟡 ŚREDNIA

**Problem**: Hasła i dane wrażliwe przechowywane w cleartext

**Rozwiązanie** (dla wrażliwych danych):
```python
# Instalacja
pip install cryptography

# app/utils/encryption.py
from cryptography.fernet import Fernet

class FieldEncryptor:
    def __init__(self, key: str):
        self.cipher = Fernet(key.encode())
    
    def encrypt(self, value: str) -> str:
        return self.cipher.encrypt(value.encode()).decode()
    
    def decrypt(self, encrypted: str) -> str:
        return self.cipher.decrypt(encrypted.encode()).decode()

# W modelach
from sqlalchemy import TypeDecorator

class EncryptedType(TypeDecorator):
    impl = db.String
    # ... implementacja
```

**Status**: ⏳ OPCJONALNE - dla SSN, payment info

---

### 11. **Brak dependency pinning**

**Lokalizacja**: `requirements.txt`  
**Ważność**: 🟡 ŚREDNIA

**Problem**:
```
# ❌ NIEBEZPIECZNE
flask>=3.0.0
flask-sqlalchemy>=3.1.0
```

Nowe wersje mogą zawierać luki bezpieczeństwa

**Rozwiązanie**:
```bash
# Utwórz requirements-prod.txt z pinowanymi wersjami
pip freeze > requirements-prod.txt

# Lub użyj Poetry
poetry lock
```

```
# ✅ LEPSZE
flask==3.0.5
flask-sqlalchemy==3.1.1
Werkzeug==3.0.1
```

**Status**: ⏳ WYMAGA POPRAWY

---

### 12. **Brak dependency vulnerability scanning**

**Lokalizacja**: CI/CD pipeline (nie zaimplementowany)  
**Ważność**: 🟡 ŚREDNIA

**Rozwiązanie**:
```bash
pip install pip-audit
pip-audit
```

**Status**: ⏳ OPCJONALNE - ale WYSOKO REKOMENDOWANE

---

### 13. **Brak error tracking (Sentry)**

**Lokalizacja**: Nie zaimplementowane  
**Ważność**: 🟡 ŚREDNIA

**Problem**: Błędy w production nie są logowane centralnie

```bash
pip install sentry-sdk
```

```python
# app/__init__.py
import sentry_sdk

sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    environment=os.getenv('FLASK_ENV'),
    traces_sample_rate=0.1,
)
```

**Status**: ⏳ WYSOKO REKOMENDOWANE

---

## ✅ CO JEST DOBRE

### Punkty Pozytywne (13 obszarów):

1. ✅ **SQL Injection Protection** - Używane SQLAlchemy ORM
2. ✅ **Input Validation** - Validators na formach
3. ✅ **Output Encoding** - Jinja2 auto-escape
4. ✅ **CSRF Protection** - flask-wtf implementacja
5. ✅ **Multi-Tenant Isolation** - middleware verify_tenant_access()
6. ✅ **Role-Based Access Control** - @role_required decorator
7. ✅ **Password Requirements** - 12+ chars, complex rules
8. ✅ **Session Management** - flask-login + timeout
9. ✅ **Audit Logging** - JSON logs per-tenant
10. ✅ **Database Backups** - manage_db.py backup
11. ✅ **Error Handling** - 404, 403, 500 handlers
12. ✅ **HSTS Header** - Present in production
13. ✅ **Email Verification** - Implementation present

---

## 📋 CHECKLIST PRE-PRODUKCYJNY

### Konfiguracja Bezpieczeństwa

- [ ] **SECRET_KEY** - Wygenerować silny klucz (MIN 32 znaki)
- [ ] **DEBUG = False** - Verified
- [ ] **TESTING = False** - Verified
- [ ] **FLASK_ENV = production** - Verified
- [ ] **SQLALCHEMY_ECHO = False** - Verified

### HTTPS/TLS

- [ ] **SSL Certificate** - Zainstalować (Let's Encrypt)
- [ ] **HTTP → HTTPS Redirect** - Implementować
- [ ] **HSTS Header** - Already present
- [ ] **Cookie Flags** - HTTPOnly + Secure + SameSite

### Database

- [ ] **Connection Encryption (SSL)** - Configure
- [ ] **Database User Privileges** - Limit permissions
- [ ] **Backups** - Test restore procedure
- [ ] **Backup Encryption** - Implementować

### Authentication

- [ ] **Password Requirements** - ✅ Present
- [ ] **Argon2 Migration** - Implementować
- [ ] **Rate Limiting Login** - ✅ Present (5/min)
- [ ] **Rate Limiting Password Reset** - Dodać
- [ ] **MFA (TOTP)** - Optional, ale recommended

### API Security

- [ ] **Rate Limiting (Redis)** - Configure
- [ ] **Input Validation** - Review all endpoints
- [ ] **Output Encoding** - Verify templates
- [ ] **CORS** - Configure properly

### Monitoring

- [ ] **Centralized Logging** - Setup (ELK/CloudWatch)
- [ ] **Error Tracking** - Setup (Sentry)
- [ ] **Security Monitoring** - Implement alerts
- [ ] **Backup Verification** - Test monthly

### Code Quality

- [ ] **Dependency Audit** - Run pip-audit
- [ ] **Static Analysis** - Run bandit
- [ ] **Security Review** - Manual code review
- [ ] **Penetration Testing** - Hire security firm

---

## 🚀 PLAN WDROŻENIA

### Faza 1: KRYTYCZNE (3-5 dni) 🔴
1. Generuj SECRET_KEY
2. Wdrożyć CSP z nonce
3. Migracja na Redis/Memcached
4. Konfiguracja cookie security flags
5. HTTPS redirect implementation

### Faza 2: POWAŻNE (1-2 tygodnie) ⚠️
1. Migracja na Argon2
2. Rate limiting password reset
3. File upload validation
4. Database connection encryption
5. Dependency pinning

### Faza 3: REKOMENDOWANE (2-3 tygodnie)
1. Sentry integration
2. pip-audit + bandit setup
3. Error handling improvements
4. Performance optimization
5. Backup encryption

### Faza 4: OPCJONALNE (1 miesiąc)
1. MFA (TOTP) implementation
2. Database field encryption
3. ELK stack setup
4. Advanced monitoring
5. Security audit byThird-party

---

## 📊 Metryki Bezpieczeństwa

| Kategoria | Status | Score |
|-----------|--------|-------|
| **Injection** | ✅ DOBRZE | 9/10 |
| **Authentication** | ⚠️ ŚREDNIE | 6/10 |
| **Sensitive Data** | 🔴 SŁABE | 3/10 |
| **Access Control** | ✅ DOBRZE | 8/10 |
| **Security Config** | 🔴 SŁABE | 4/10 |
| **Logging & Monitoring** | 🟡 ŚREDNIE | 5/10 |
| **Overall** | **⚠️ ŚREDNIE** | **5.8/10** |

---

## 🔧 Konkretne Komendy do Wykonania

```bash
# 1. Generuj SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# 2. Zainstaluj Argon2
pip install argon2-cffi

# 3. Zainstaluj Redis client
pip install redis

# 4. Uruchom security audit
pip install bandit pylint pip-audit
bandit -r app/
pip-audit

# 5. Sprawdź dependencies
pip freeze > requirements-prod.txt

# 6. Test aplikacji
pytest tests/
```

---

## 📞 Rekomendacje

### Natychmiastowe (przed produkcją):
1. ✅ Fix SECRET_KEY configuration
2. ✅ Implement CSP nonce
3. ✅ Setup Redis for rate limiting
4. ✅ Add cookie security flags
5. ✅ Implement HTTPS redirect

### Krótkookresowe (pierwszy miesiąc):
1. Migracja na Argon2
2. Setup Sentry
3. Dependency pinning
4. File upload security
5. Database encryption

### Długookresowe (roadmap):
1. MFA implementation
2. Advanced monitoring
3. Penetration testing
4. Load balancing setup
5. DR procedures

---

## 📚 Referencje

- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/latest/security/)
- [NIST Password Guidelines](https://pages.nist.gov/800-63-3/)
- [CSP MDN Guide](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [Redis Security](https://redis.io/docs/management/security/)

---

**Status Raportu**: ⏳ WYMAGA AKCJI  
**Ostatnia Aktualizacja**: 2026-02-19  
**Następna Przegląd**: Po implementacji Fazy 1

