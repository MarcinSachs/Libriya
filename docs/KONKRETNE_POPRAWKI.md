# 🔧 Konkretne Poprawki - Kod do Implementacji




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

