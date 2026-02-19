"""
Destructive reset of Alembic migrations for local development.

WARNING: This script will delete all files in `migrations/versions` (except __init__.py),
remove the `alembic_version` table from the configured database, create a new
single base migration (revision '000000000001') and then run SQLAlchemy's
`db.create_all()` to create all tables from current models.

Only run in development. The script attempts to refuse running when FLASK_ENV
or APP_ENV is set to 'production'.
"""
import os
import glob
import datetime
import traceback
import sqlalchemy as sa

# Make imports relative to package
try:
    from app import create_app, db
except Exception:
    # Allow running from repository root
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from app import create_app, db

BASE_REVISION = '000000000001'


def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    versions_dir = os.path.join(base_dir, 'migrations', 'versions')

    print('Running destructive migration reset (development only)')
    print('Repository base:', base_dir)

    # Safety check: don't run in production
    env = os.environ.get('FLASK_ENV') or os.environ.get('APP_ENV') or os.environ.get('ENV')
    if env and env.lower() == 'production':
        print('Refusing to run in production environment (FLASK_ENV/APP_ENV=production)')
        return 1

    # Ensure migrations/versions exists
    if not os.path.isdir(versions_dir):
        os.makedirs(versions_dir, exist_ok=True)

    # Remove existing revision files (but keep __init__.py if present)
    removed = []
    for path in glob.glob(os.path.join(versions_dir, '*.py')):
        name = os.path.basename(path)
        if name == '__init__.py':
            continue
        try:
            os.remove(path)
            removed.append(name)
        except Exception as e:
            print('Could not remove', path, e)

    print(f'Removed {len(removed)} migration file(s):', removed)

    # Create a single base (no-op) revision file
    rev_file = os.path.join(versions_dir, f'{BASE_REVISION}_initial.py')
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    content = f"""\"\"\"Empty initial migration created by scripts/reset_migrations.py

Revision ID: {BASE_REVISION}
Revises: 
Create Date: {now}
\"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '{BASE_REVISION}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # no-op: database schema will be created via SQLAlchemy create_all()
    pass


def downgrade():
    pass
"""
    with open(rev_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print('Wrote base revision file:', rev_file)

    # Now open app and operate on DB
    app = create_app()
    try:
        with app.app_context():
            engine = db.engine

            # If using sqlite file-based DB, attempt to remove the file first to avoid locks
            try:
                url = getattr(engine, 'url', None)
                db_path = None
                if url is not None and getattr(url, 'drivername', None) == 'sqlite':
                    db_path = getattr(url, 'database', None)
                    if db_path and db_path != ':memory:':
                        # Resolve relative paths against Flask instance path
                        if not os.path.isabs(db_path):
                            db_path = os.path.abspath(os.path.join(app.instance_path or os.getcwd(), db_path))

                        # Dispose engine to close open connections
                        try:
                            engine.dispose()
                        except Exception:
                            pass

                        if os.path.exists(db_path):
                            try:
                                print('Removing sqlite database file to avoid lock:', db_path)
                                os.remove(db_path)
                            except Exception as e:
                                print('Could not remove sqlite file:', e)

                        # Re-get engine after deletion
                        engine = db.engine
            except Exception as e:
                print('Warning: could not check/remove sqlite db file:', e)

            inspector = sa.inspect(engine)
            conn = engine.connect()

            # Drop alembic_version table if exists
            if 'alembic_version' in inspector.get_table_names():
                print('Dropping existing alembic_version table')
                conn.execute(sa.text('DROP TABLE alembic_version'))

            # Create alembic_version and set it to BASE_REVISION
            print('Creating alembic_version table and stamping to', BASE_REVISION)
            conn.execute(sa.text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"))
            # Clean any existing rows
            conn.execute(sa.text("DELETE FROM alembic_version"))
            conn.execute(sa.text("INSERT INTO alembic_version (version_num) VALUES (:v)"), {'v': BASE_REVISION})

            # Close the stamping connection and dispose engine to release locks
            try:
                conn.close()
            except Exception:
                pass
            try:
                engine.dispose()
            except Exception:
                pass

            # Re-acquire engine after disposal
            engine = db.engine

            # Create all SQLAlchemy tables
            print('Creating all tables via SQLAlchemy (db.create_all())')

            # Ensure no active sessions
            try:
                db.session.remove()
            except Exception:
                pass

            # Retry loop for database locked errors
            import time
            attempts = 5
            for attempt in range(1, attempts + 1):
                try:
                    # If sqlite, open a fresh connection and set busy timeout to wait for locks
                    try:
                        with engine.connect() as c:
                            c.execute(sa.text('PRAGMA busy_timeout = 5000'))
                            c.execute(sa.text("PRAGMA journal_mode = DELETE"))
                    except Exception:
                        pass

                    db.create_all()
                    print('   ✓ Tables created')
                    break
                except Exception as e:
                    if 'database is locked' in str(e).lower() and attempt < attempts:
                        print(f"   ⚠ Database is locked, retrying ({attempt}/{attempts})...")
                        time.sleep(1)
                        # attempt to dispose and reconnect
                        try:
                            engine.dispose()
                        except Exception:
                            pass
                        engine = db.engine
                        continue
                    raise

            print('Done. Database schema created and alembic stamped to base revision.')
    except Exception as e:
        print('ERROR during reset:', e)
        traceback.print_exc()
        return 2

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
