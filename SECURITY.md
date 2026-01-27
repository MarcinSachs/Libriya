# Security Documentation for Libriya

## Security Enhancements Summary

This document outlines the security improvements implemented in the Libriya application.

---

## 1. **Environment Variables & Secrets Management**

### Changes Made:
- **SECRET_KEY** is now **required** via environment variable
- Application will crash on startup if `SECRET_KEY` is not set
- This prevents accidental exposure of hardcoded secrets

### Setup:
```bash
# Generate a secure random key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Set environment variable
export SECRET_KEY="your-generated-key-here"

# For Windows:
set SECRET_KEY=your-generated-key-here
```

### Usage:
```python
# config.py loads from environment automatically
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("CRITICAL: SECRET_KEY environment variable is not set!")
```

---

## 2. **Debug Mode Control**

### Changes Made:
- Debug mode is now controlled by `FLASK_ENV` environment variable
- `debug=True` **only** when `FLASK_ENV=development`
- Production deployments will run with `debug=False` by default

### Setup:
```bash
# Development
export FLASK_ENV=development

# Production
export FLASK_ENV=production
```

### Code:
```python
# libriya.py
debug_mode = os.environ.get('FLASK_ENV') == 'development'
app.run(debug=debug_mode)
```

---

## 3. **Security Headers**

### Changes Made:
The following HTTP security headers are automatically added to every response:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type sniffing attacks |
| `X-Frame-Options` | `SAMEORIGIN` | Clickjacking protection |
| `X-XSS-Protection` | `1; mode=block` | XSS filter activation |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Forces HTTPS (1 year) |
| `Content-Security-Policy` | Restricted | Prevents unauthorized script/resource loading |

### Implementation:
```python
# app/__init__.py
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    return response
```

---

## 4. **Rate Limiting on Login**

### Changes Made:
- Login endpoint now has **rate limiting**: 5 attempts per minute
- Prevents brute-force password attacks
- Uses client IP address for rate limit tracking

### Setup:
```bash
pip install flask-limiter
```

### Code:
```python
# app/routes/auth.py
@bp.route("/login/", methods=['POST'])
@limiter.limit("5 per minute")
def login_post():
    # ...
```

### Behavior:
- User can attempt login 5 times per minute
- On 6th attempt: HTTP 429 (Too Many Requests) response
- Counter resets after 1 minute

---

## 5. **File Upload Security (SSRF Prevention)**

### Changes Made:
Comprehensive validation for cover image URLs to prevent Server-Side Request Forgery (SSRF):

#### Validations:
1. **Protocol Whitelist**: Only HTTP and HTTPS allowed
2. **Private IP Blocking**: Blocks attempts to access:
   - `localhost`, `127.0.0.1`, `0.0.0.0`
   - Private IP ranges (10.x.x.x, 172.16.x.x, 192.168.x.x)
3. **Size Limits**:
   - Max 5MB per file (checked both on Content-Length header and actual download)
4. **File Type Validation**:
   - Only `.jpg`, `.jpeg`, `.png`, `.gif` allowed
5. **Timeout Protection**: 10-second timeout on HTTP requests

### Code:
```python
# app/routes/books.py - Security checks in cover_url handling
parsed_url = urlparse(cover_url)

# Check protocol
if parsed_url.scheme not in ['http', 'https']:
    raise ValueError("Invalid URL scheme. Only HTTP(S) allowed.")

# Check for private IPs
if parsed_url.netloc in ['localhost', '127.0.0.1', '0.0.0.0']:
    raise ValueError("Cannot access local network addresses.")

# Check size limits
if downloaded_size > 5 * 1024 * 1024:
    raise ValueError("File too large. Maximum 5MB allowed.")
```

---

## 6. **Request Size Limiting**

### Changes Made:
- Maximum request size limited to **16MB**
- Prevents DoS attacks from oversized uploads

### Code:
```python
# config.py
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max request size
```

### Usage:
If user tries to upload file larger than 16MB, Flask returns HTTP 413 (Payload Too Large).

---

## 7. **ISBN Validation**

### Changes Made:
- ISBN field now validates both ISBN-10 and ISBN-13 formats
- Accepts hyphens and spaces but validates digits only
- Custom validator with clear error messages

### Code:
```python
# app/forms.py
class ISBNValidator:
    def __call__(self, form, field):
        if field.data:
            isbn = field.data.replace('-', '').replace(' ', '')
            if not isbn.isdigit() or len(isbn) not in [10, 13]:
                raise ValidationError('Invalid ISBN format')

class BookForm(FlaskForm):
    isbn = StringField(_('ISBN'), validators=[Optional(), ISBNValidator()])
```

---

## 8. **Audit Logging System**

### Changes Made:
Comprehensive audit trail for sensitive operations.

#### Events Logged:
- User creation
- User deletion
- Role modifications
- Password changes
- Failed login attempts
- Book deletion
- Profile updates
- Library operations

#### Log Location:
```
logs/audit.log
```

#### Log Format:
```
2026-01-27 15:30:45 - audit - INFO - USER_CREATED | User: admin (ID: 1) | IP: 192.168.1.100 | New user created: john | Target ID: 42 | Details: {'username': 'john', 'email': 'john@example.com'}
```

#### Log Rotation:
- Files rotate at 10MB
- Up to 10 backup files retained
- Old logs automatically archived

### Usage:
```python
# app/utils/audit_log.py
from app.utils.audit_log import log_user_created, log_user_deleted

log_user_created(user.id, user.username, user.email)
log_user_deleted(user.id, user.username)
```

### Viewing Logs:
```bash
# View audit logs (Unix/Linux/Mac)
tail -f logs/audit.log

# Search for specific events
grep "USER_DELETED" logs/audit.log
grep "FAILED_LOGIN" logs/audit.log
```

---

## 9. **Existing Security Features** ✅

### Already Implemented:
- ✅ **Password Hashing**: Werkzeug's `generate_password_hash()` using bcrypt
- ✅ **CSRF Protection**: Flask-WTF with CSRF tokens on all forms
- ✅ **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
- ✅ **Session Management**: Flask-Login for secure user sessions
- ✅ **Role-Based Access Control**: Custom `@role_required()` decorator
- ✅ **File Upload Security**: `secure_filename()` and extension validation
- ✅ **Error Handling**: 404/500 pages without sensitive information

---

## Setup Instructions

### 1. Install Dependencies:
```bash
pip install -r requirements.txt
```

### 2. Create `.env` File:
```bash
# Copy example file
cp .env.example .env

# Edit .env and set required values:
# - FLASK_ENV=development (or production)
# - SECRET_KEY=your-strong-random-key
# - DATABASE_URL=your-database-url (optional, defaults to SQLite)
```

### 3. Generate SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Run Application:
```bash
python libriya.py
```

---

## Security Best Practices

### For Administrators:

1. **Keep Dependencies Updated**:
   ```bash
   pip install --upgrade -r requirements.txt
   ```

2. **Monitor Audit Logs**:
   ```bash
   tail -f logs/audit.log
   ```

3. **Use Strong Secrets**:
   - Generate with 32+ characters
   - Use random alphanumeric + special characters
   - Store securely in environment variables only

4. **Enable HTTPS**:
   - Use TLS/SSL certificates in production
   - Set `Strict-Transport-Security` header

5. **Regular Backups**:
   - Backup database regularly
   - Store backups securely

6. **Database Security**:
   - Use PostgreSQL in production (not SQLite)
   - Create database user with limited permissions
   - Don't expose database publicly

### For Deployment:

1. **Environment Variables**:
   ```bash
   export FLASK_ENV=production
   export SECRET_KEY="strong-random-key"
   export DATABASE_URL="postgresql://..."
   ```

2. **Use WSGI Server**:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 libriya:app
   ```

3. **Reverse Proxy**:
   - Use Nginx or Apache in front
   - Enable HTTPS/TLS
   - Set security headers

4. **Firewall**:
   - Restrict database access
   - Allow only necessary ports
   - Monitor for suspicious activity

---

## Testing Security

### Test Failed Login Rate Limiting:
```bash
# Try logging in with wrong password 6 times in quick succession
# On 6th attempt, should get 429 Too Many Requests
```

### Test SSRF Protection:
```python
# Try uploading with URLs like:
# - http://localhost/admin
# - http://192.168.1.1
# - http://127.0.0.1

# All should be blocked with error messages
```

### Test File Size Limits:
```bash
# Try uploading file > 16MB
# Should get error: "Payload Too Large"
```

---

## Incident Response

### If Compromise is Suspected:

1. **Immediately Change SECRET_KEY**:
   ```bash
   export SECRET_KEY="new-secret-key"
   # Restart application
   ```

2. **Review Audit Logs**:
   ```bash
   grep "ROLE_MODIFIED\|USER_DELETED\|FAILED_LOGIN" logs/audit.log
   ```

3. **Force Password Resets**:
   - Force all users to reset passwords
   - Clear active sessions

4. **Monitor Network Traffic**:
   - Check for suspicious connections
   - Review failed login attempts

5. **Update Dependencies**:
   - Check for vulnerable packages
   - Run: `pip list --outdated`

---

## References

- [OWASP Top 10 Web Application Security Risks](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/latest/security/)
- [SSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Rate Limiting](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html#rate-limit-login-attempts)

---

**Last Updated**: January 27, 2026
**Version**: 1.0
