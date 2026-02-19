import os
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

BASE = os.path.dirname(os.path.dirname(__file__))
print('BASE', BASE)
migrations_dir = os.path.join(BASE, 'migrations')
print('MIGRATIONS_DIR', migrations_dir)

cfg = Config(os.path.join(migrations_dir, 'alembic.ini'))
cfg.set_main_option('script_location', migrations_dir)
script = ScriptDirectory.from_config(cfg)
print('Available revisions count:', len(list(script.walk_revisions())))
print('Heads from script:', script.get_heads())

# Inspect DB alembic_version table
from app import create_app, db
app = create_app()
with app.app_context():
    conn = db.engine.connect()
    try:
        res = conn.execute(text('SELECT * FROM alembic_version'))
        rows = res.fetchall()
        print('alembic_version rows:', rows)
    except Exception as e:
        print('Error reading alembic_version:', e)
    # list tables
    try:
        inspector = __import__('sqlalchemy').inspect(db.engine)
        print('Tables:', inspector.get_table_names())
    except Exception as e:
        print('Error listing tables:', e)

print('Done')
