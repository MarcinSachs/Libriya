# ⚡ Performance & Optimization Guide

## 📊 Performance Metrics Baseline

| Metrika | Obecna | Target | Status |
|---------|--------|--------|--------|
| Page Load Time | ~800ms | <500ms | ⚠️ |
| Time to Interactive | ~1.5s | <1s | ⚠️ |
| Database Queries | ~8 per page | <3 per page | ⚠️ |
| Memory Usage | ~150MB | <100MB | ⚠️ |
| CSS Bundle | ~50KB | <30KB | ⚠️ |

---

## 1. Database Optimization

### 1.1 Query Optimization

#### Problem: N+1 Queries
```python
# ❌ BAD - N+1 problem (1 query for users + N queries for each tenant)
users = User.query.all()
for user in users:
    tenant = user.tenant  # Extra query!

# ✅ GOOD - Use eager loading
users = User.query.options(joinedload(User.tenant)).all()
```

#### Problem: Missing Indexes
```python
# app/models.py - Sprawdzić indeksy
class User(db.Model):
    # Dodaj index na kolumny frequently filtered
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, index=True)
```

#### Migration: Add Missing Indexes
```bash
# Create migration
flask db migrate -m "add_missing_indexes"

# alembic/versions/xxx_add_missing_indexes.py
from alembic import op

def upgrade():
    # Add indexes na kolumny używane w WHERE clauses
    op.create_index('idx_user_email', 'user', ['email'])
    op.create_index('idx_user_tenant_id', 'user', ['tenant_id'])
    op.create_index('idx_library_tenant_id', 'library', ['tenant_id'])
    op.create_index('idx_book_tenant_id', 'book', ['tenant_id'])
    op.create_index('idx_loan_tenant_id', 'loan', ['tenant_id'])
    op.create_index('idx_audit_log_tenant_id', 'audit_log', ['tenant_id'])

def downgrade():
    op.drop_index('idx_audit_log_tenant_id')
    op.drop_index('idx_loan_tenant_id')
    # ... itd
```

### 1.2 Query Caching

```python
# config.py
CACHE_TYPE = 'simple'  # or redis
CACHE_DEFAULT_TIMEOUT = 300

# app/__init__.py
from flask_caching import Cache
cache = Cache(app)

# app/routes/admin.py
@bp.route('/tenants')
@cache.cached(timeout=600, key_prefix='tenants_list')
def tenants_list():
    """Cache tenant list for 10 minutes"""
    tenants = Tenant.query.all()
    return render_template('admin/tenants_list.html', tenants=tenants)

# Invalidate cache when data changes
@bp.route('/tenants/add', methods=['POST'])
def tenant_add():
    # ... create tenant ...
    cache.delete('tenants_list')  # Invalidate cache
    return redirect(...)
```

### 1.3 Database Connection Pooling

```python
# config.py
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 20,
    'pool_recycle': 3600,
    'pool_pre_ping': True,  # Verify connections are alive
    'max_overflow': 40,
    'connect_args': {
        'connect_timeout': 10
    }
}
```

---

## 2. Frontend Optimization

### 2.1 CSS/JS Minification

```bash
# Install tools
npm install -g tailwindcss cssnano terser

# Build process
npm run build:css
npm run build:js
```

### 2.2 Asset Compression

```python
# app/__init__.py
from flask_compress import Compress
Compress(app)

# app/static/ structure
static/
├── css/
│   ├── main.css (development)
│   └── main.min.css (production)
├── js/
│   ├── app.js (development)
│   └── app.min.js (production)
└── uploads/
```

### 2.3 Template Caching

```python
# app/__init__.py
app.jinja_env.cache = {}
app.jinja_env.auto_reload = False  # Production

# Precompile templates
from flask import compile_templates
compile_templates('app/templates')
```

### 2.4 Image Optimization

```python
# app/services/image_optimizer.py
from PIL import Image
import os

def optimize_image(file_path, max_width=800, quality=85):
    """Optimize uploaded image"""
    img = Image.open(file_path)
    
    # Resize if too large
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
    
    # Convert to RGB if PNG
    if img.mode == 'RGBA':
        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
        rgb_img.paste(img, mask=img.split()[3])
        img = rgb_img
    
    # Save optimized
    img.save(file_path, 'JPEG', quality=quality, optimize=True)
```

---

## 3. API Optimization

### 3.1 Pagination

```python
# app/routes/admin.py
@bp.route('/tenants')
def tenants_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    tenants = Tenant.query.paginate(page=page, per_page=per_page)
    
    return render_template('admin/tenants_list.html', 
                          tenants=tenants.items,
                          total_pages=tenants.pages,
                          current_page=page)
```

### 3.2 Lazy Loading

```python
# Load relationships only when needed
class Book(db.Model):
    # Change lazy loading strategy
    comments = db.relationship('Comment', lazy='select')  # Load on demand
    loans = db.relationship('Loan', lazy='select')
    
    # Use selectinload in queries where needed
    # books = Book.query.options(selectinload(Book.comments)).all()
```

### 3.3 Response Compression

```python
# config.py
COMPRESS_MIMETYPES = [
    'text/html',
    'text/css',
    'application/json',
    'application/javascript'
]

# Already configured with Flask-Compress
```

---

## 4. Caching Strategy

### 4.1 Browser Caching

```python
# app/__init__.py
@app.after_request
def set_cache_headers(response):
    """Set cache headers for static files"""
    if request.path.startswith('/static/'):
        # Cache static files for 30 days
        response.cache_control.max_age = 2592000
        response.cache_control.public = True
    elif request.path in ['/', '/dashboard']:
        # Don't cache HTML pages
        response.cache_control.no_cache = True
        response.cache_control.must_revalidate = True
    else:
        # Default: cache for 1 hour
        response.cache_control.max_age = 3600
    
    return response
```

### 4.2 Server-Side Caching

```python
from flask_caching import Cache

cache = Cache(config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': 'redis://localhost:6379/0'
})

# Cache frequently accessed data
@cache.cached(timeout=3600)
def get_tenant_statistics(tenant_id):
    """Cache tenant stats for 1 hour"""
    stats = {
        'users': User.query.filter_by(tenant_id=tenant_id).count(),
        'books': Book.query.filter_by(tenant_id=tenant_id).count(),
        'loans': Loan.query.filter_by(tenant_id=tenant_id).count(),
    }
    return stats
```

---

## 5. Async & Background Tasks

### 5.1 Celery for Background Jobs

```bash
pip install celery redis
```

```python
# app/celery.py
from celery import Celery

celery = Celery('libriya')
celery.config_from_object('celeryconfig')

# celeryconfig.py
broker_url = 'redis://localhost:6379/0'
result_backend = 'redis://localhost:6379/0'
task_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'

# app/tasks.py
from app.celery import celery

@celery.task
def send_email_async(email, subject, body):
    """Send email in background"""
    send_email(email, subject, body)

@celery.task
def backup_database():
    """Backup database every night"""
    import subprocess
    subprocess.run(['python', 'backup_db.py'])

@celery.task
def cleanup_old_logs():
    """Delete audit logs older than 90 days"""
    from app.models import AuditLog
    from datetime import datetime, timedelta
    
    cutoff = datetime.utcnow() - timedelta(days=90)
    AuditLog.query.filter(AuditLog.timestamp < cutoff).delete()
    db.session.commit()

# app/routes/admin.py - Use async task
from app.tasks import send_email_async

@bp.route('/tenants/add', methods=['POST'])
def tenant_add():
    tenant = Tenant(...)
    db.session.add(tenant)
    db.session.commit()
    
    # Send welcome email in background
    send_email_async.delay(
        tenant.admin.email,
        'Welcome to Libriya',
        'Your tenant has been created'
    )
    
    return redirect(...)
```

### 5.2 Scheduled Tasks

```python
# app/utils/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

def init_scheduler(app):
    """Initialize background scheduler"""
    scheduler = BackgroundScheduler()
    
    # Backup database daily at 2 AM
    scheduler.add_job(
        func=backup_database,
        trigger="cron",
        hour=2,
        minute=0,
        id='backup_db'
    )
    
    # Cleanup old logs monthly
    scheduler.add_job(
        func=cleanup_old_logs,
        trigger="cron",
        day=1,
        hour=3,
        id='cleanup_logs'
    )
    
    # Send daily digest emails
    scheduler.add_job(
        func=send_daily_digest,
        trigger="cron",
        hour=9,
        minute=0,
        id='daily_digest'
    )
    
    scheduler.start()
    return scheduler

# app/__init__.py
from app.utils.scheduler import init_scheduler

def create_app(config_class=Config):
    # ... existing code ...
    
    with app.app_context():
        init_scheduler(app)
    
    return app
```

---

## 6. Monitoring & Profiling

### 6.1 Flask Profiling

```bash
pip install flask-debugtoolbar
```

```python
# app/__init__.py (development only)
if app.debug:
    from flask_debugtoolbar import DebugToolbarExtension
    toolbar = DebugToolbarExtension(app)
```

### 6.2 Request Profiling

```python
# app/utils/profiler.py
import time
from functools import wraps

def profile_request(f):
    """Decorator to profile request execution time and database queries"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        result = f(*args, **kwargs)
        
        end_time = time.time()
        duration = end_time - start_time
        
        if duration > 1.0:  # Log slow requests > 1 second
            app.logger.warning(f"Slow request: {request.path} took {duration:.2f}s")
        
        return result
    
    return decorated_function

# Usage
@bp.route('/books')
@profile_request
def books_list():
    pass
```

### 6.3 Application Performance Monitoring (APM)

```bash
pip install sentry-sdk
```

```python
# app/__init__.py
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

if not app.debug:
    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        integrations=[FlaskIntegration()],
        traces_sample_rate=0.1,
        environment=os.getenv('ENVIRONMENT', 'production')
    )
```

---

## 7. Load Testing

```bash
pip install locust
```

```python
# locustfile.py
from locust import HttpUser, between, task

class LibriyaUser(HttpUser):
    wait_time = between(1, 5)
    
    @task(3)
    def view_books(self):
        self.client.get('/books')
    
    @task(1)
    def view_book_detail(self):
        self.client.get('/books/1')
    
    def on_start(self):
        self.client.post('/auth/login', json={
            'email_or_username': 'testuser',
            'password': 'test123'
        })
```

Run:
```bash
locust -f locustfile.py --host=http://localhost:5001
# Open http://localhost:8089
```

---

## 8. Production Deployment Optimization

### 8.1 Gunicorn Configuration

```bash
pip install gunicorn
```

```python
# gunicorn_config.py
import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 5
```

Run:
```bash
gunicorn -c gunicorn_config.py --bind 0.0.0.0:5001 libriya:app
```

### 8.2 Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/libriya
upstream gunicorn {
    server 127.0.0.1:5001;
}

server {
    listen 443 ssl http2;
    server_name libriya.com *.libriya.com;
    
    ssl_certificate /etc/letsencrypt/live/libriya.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/libriya.com/privkey.pem;
    
    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_min_length 1000;
    
    # Cache static files
    location /static/ {
        alias /app/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location / {
        proxy_pass http://gunicorn;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name libriya.com *.libriya.com;
    return 301 https://$server_name$request_uri;
}
```

---

## Checklist Optymalizacji

- [ ] Database indexes na todas kolumny filtrowane
- [ ] Query optimization (no N+1 problems)
- [ ] Caching strategy implemented
- [ ] Static assets minified
- [ ] Compression enabled (gzip)
- [ ] CDN configured dla static files
- [ ] Browser caching headers set
- [ ] Background tasks implemented
- [ ] Async operations where applicable
- [ ] Monitoring & alerting configured
- [ ] Load testing performed
- [ ] Performance benchmarks met

