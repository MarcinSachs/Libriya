# Production Deployment Guide

## 🚀 Pre-Deployment Checklist

### 1. Security Configuration ✅

```bash
# Generate SECRET_KEY
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"

# Add to .env.production
SECRET_KEY=<wygenerowana_wartość>
```

### 2. Redis Setup (Required for Production) 🔴

Rate limiting **MUSI** używać Redis/Memcached w production!

**Option A: Docker (Recommended)**
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

**Option B: System Package**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis-server

# macOS
brew install redis
brew services start redis
```

**Verify connection:**
```bash
redis-cli ping
# Output: PONG
```

### 3. Install Production Dependencies

```bash
# Zainstaluj requirements
pip install -r requirements-prod.txt

# Zainstaluj additional production packages
pip install redis argon2-cffi gunicorn python-magic sentry-sdk
```

**Update requirements.txt or create requirements-prod.txt:**
```
flask==3.0.5
flask-sqlalchemy==3.1.1
flask-migrate==4.0.5
flask-wtf==1.2.1
python-dotenv==1.0.0
pymysql==1.1.0
wtforms==3.1.1
requests==2.31.0
flask-login==0.6.3
Flask-Babel==4.0.0
flask-session==0.5.0
wtforms-sqlalchemy==0.3
flask-limiter==3.6.0
isbnlib==3.10.14
Pillow==10.1.0
APScheduler==3.10.4
python-json-logger==2.0.7
flask-caching==2.1.0
redis==5.0.1
argon2-cffi==23.2.0
gunicorn==21.2.0
python-magic==0.4.27
sentry-sdk==1.39.1
```

### 4. Database Setup

**MariaDB/MySQL (Production Recommended)**
```sql
CREATE DATABASE libriya_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'libriya_user'@'localhost' IDENTIFIED BY 'strong_password_here';
GRANT ALL PRIVILEGES ON libriya_db.* TO 'libriya_user'@'localhost';
FLUSH PRIVILEGES;
```

**Run migrations:**
```bash
flask db upgrade
```

### 5. SSL/TLS Certificate

**Using Let's Encrypt with Certbot:**
```bash
sudo certbot certonly --standalone -d example.com -d www.example.com

# Auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

### 6. Systemd Service File

Create `/etc/systemd/system/libriya.service`:

```ini
[Unit]
Description=Libriya Flask Application
After=network.target redis.service mysql.service

[Service]
Type=notify
User=www-data
WorkingDirectory=/var/www/libriya
ExecStart=/var/www/libriya/venv/bin/gunicorn \
    --workers 4 \
    --worker-class sync \
    --bind 0.0.0.0:5000 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    "libriya:create_app()"

Environment="FLASK_ENV=production"
Environment="PATH=/var/www/libriya/venv/bin"
EnvironmentFile=/var/www/libriya/.env.production

Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

### 7. Nginx Configuration

Create `/etc/nginx/sites-available/libriya`:

```nginx
upstream libriya {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name example.com *.example.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com *.example.com;
    
    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Other security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy configuration
    location / {
        proxy_pass http://libriya;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Static files
    location /static/ {
        alias /var/www/libriya/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Uploads
    location /uploads/ {
        alias /var/www/libriya/app/static/uploads/;
        expires 7d;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/libriya /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 8. Start Services

```bash
# Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# MySQL
sudo systemctl start mysql
sudo systemctl enable mysql

# Libriya
sudo systemctl start libriya
sudo systemctl enable libriya

# Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### 9. Verification

```bash
# Check Libriya service
sudo systemctl status libriya

# Check logs
sudo journalctl -u libriya -f

# Health check
curl https://localhost/health  # jeśli endpoint istnieje

# Check SSL
curl -I https://example.com
```

### 10. Automated Backups

Create `/var/www/libriya/backup_scheduler.py`:

```python
from apscheduler.schedulers.background import BackgroundScheduler
from app import create_app, db
import os
import subprocess
from datetime import datetime

def scheduled_backup():
    """Run database backup at scheduled time"""
    app = create_app()
    with app.app_context():
        from manage_db import backup_database
        print(f"[{datetime.now()}] Starting automated backup...")
        if backup_database():
            print("✓ Backup completed successfully")
        else:
            print("✗ Backup failed")

# This would be called from app initialization
def init_backup_scheduler(app):
    scheduler = BackgroundScheduler()
    
    # Daily backup at 2:00 AM
    hour = os.getenv('BACKUP_SCHEDULE_HOUR', '2')
    minute = os.getenv('BACKUP_SCHEDULE_MINUTE', '0')
    
    scheduler.add_job(
        scheduled_backup,
        'cron',
        hour=int(hour),
        minute=int(minute),
        id='db_backup'
    )
    
    scheduler.start()
    return scheduler
```

### 11. Monitoring and Alerts

Install Sentry:
```bash
pip install sentry-sdk
```

Configure in `app/__init__.py`:
```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    integrations=[FlaskIntegration()],
    traces_sample_rate=0.1,
    environment=os.getenv('FLASK_ENV'),
    send_default_pii=False
)
```

### 12. Security Scanning

Run before deployment:
```bash
# Dependency audit
pip-audit

# Static analysis
bandit -r app/

# OWASP ZAP (manual or automated)
```

### 13. Performance Tuning

**Gunicorn workers calculation:**
```
workers = (2 × cpu_count) + 1
```

For 2-core server: `--workers 5`

**Database connection pool:**
```python
# config.py - already configured
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
    'max_overflow': 20,
}
```

### 14. Backup Restoration Test

```bash
# Backup
python manage_db.py backup

# List backups
ls -lh backups/

# To restore (MySQL)
mysql -u user -p database < backups/libriya_backup_*.sql

# To restore (SQLite)
cp backups/libriya_backup_*.db libriya.db
```

### 15. Load Testing (Optional but Recommended)

```bash
pip install locust

# Create locustfile.py and run
locust -f locustfile.py --host=https://example.com
```

---

## 🚨 Post-Deployment Checklist

- [ ] SSL certificate installed and valid
- [ ] HTTPS redirect working
- [ ] Rate limiting with Redis enabled
- [ ] Database backups automated
- [ ] Error tracking (Sentry) receiving events
- [ ] All environment variables set correctly
- [ ] Database migrations completed
- [ ] Static files served correctly
- [ ] Email notifications working
- [ ] Health check endpoint responding
- [ ] Logs are being written
- [ ] Backup restoration tested
- [ ] Security headers present
- [ ] Dependencies up-to-date
- [ ] Performance acceptable (< 200ms response time)

---

## 📞 Troubleshooting

### Redis Connection Error
```bash
# Check if Redis is running
redis-cli ping

# Restart Redis
sudo systemctl restart redis-server
```

### Database Connection Error
```bash
# Check credentials in .env.production
# Test connection
mysql -u libriya_user -p libriya_db -h localhost

# Check logs
sudo journalctl -u libriya -f
```

### SSL Certificate Error
```bash
# Check certificate validity
sudo certbot certificates

# Renew if needed
sudo certbot renew --force-renewal
```

### Out of Memory
```bash
# Increase swap or add more RAM
# Reduce worker count in gunicorn config
```

---

## 🔄 Rollback Plan

If something goes wrong:
```bash
# Stop services
sudo systemctl stop libriya nginx

# Restore backup
mysql -u user -p database < backups/libriya_backup_<date>.sql

# Restart
sudo systemctl start mysql
sudo systemctl start libriya
sudo systemctl start nginx

# Verify
sudo systemctl status libriya
```

---

**Deployment Status**: Ready for Production Deployment ✅

