import os, sqlite3
p = os.path.abspath('instance/libriya.db')
print('path:', p)
print('exists:', os.path.exists(p))
try:
    print('size:', os.path.getsize(p))
except Exception as e:
    print('size error:', e)
print('readable:', os.access(p, os.R_OK))
print('writable:', os.access(p, os.W_OK))
try:
    conn = sqlite3.connect(p)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cur.fetchall()
    print('tables:', tables)
    conn.close()
except Exception as e:
    print('sqlite error:', e)
