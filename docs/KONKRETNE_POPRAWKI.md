# 🔧 Konkretne Poprawki - Kod do Implementacji


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

