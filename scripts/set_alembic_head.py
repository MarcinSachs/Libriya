import os
import sys
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

# Ensure repo root is on sys.path so 'app' imports work when running this script directly
repo = os.path.dirname(os.path.dirname(__file__))
if repo not in sys.path:
    sys.path.insert(0, repo)

from app import create_app, db

migrations_dir = os.path.join(repo, 'migrations')

cfg = Config(os.path.join(migrations_dir, 'alembic.ini'))
cfg.set_main_option('script_location', migrations_dir)
script = ScriptDirectory.from_config(cfg)
heads = script.get_heads()
print('Available heads from script:', heads)
if not heads:
    raise SystemExit('No heads found in migrations')
head = heads[0]

app = create_app()
with app.app_context():
    conn = db.engine.connect()
    try:
        # Delete existing rows in alembic_version (if any) and insert chosen head
        conn.execute(text('DELETE FROM alembic_version'))
        conn.execute(text('INSERT INTO alembic_version (version_num) VALUES (:v)'), {'v': head})
        print('alembic_version set to', head)
    finally:
        conn.close()
