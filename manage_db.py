#!/usr/bin/env python
"""
Database Setup and Migration Script
Helps with initial setup and migrations
"""
import os
import sys
from flask import Flask
from flask_migrate import Migrate, upgrade, current, stamp
from app import create_app, db
from app.seeds.seed import seed_database


def create_database_if_not_exists():
    """Create database if it doesn't exist (for MySQL/MariaDB)"""
    from sqlalchemy import create_engine
    from sqlalchemy.exc import OperationalError
    import re

    database_url = os.getenv('DATABASE_URL', '')

    if 'mysql' in database_url or 'mariadb' in database_url:
        # Parse database name from URL
        match = re.search(r'/([^/?]+)(\?|$)', database_url)
        if match:
            db_name = match.group(1)
            # Create URL without database name
            base_url = database_url.replace(f'/{db_name}', '/mysql')

            try:
                engine = create_engine(base_url)
                with engine.connect() as conn:
                    conn.execute(
                        f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                    print(f"✓ Database '{db_name}' ready")
                engine.dispose()
            except OperationalError as e:
                print(f"✗ Error creating database: {e}")
                return False
    return True


def check_migrations_needed():
    """Check if there are pending migrations"""
    app = create_app()
    with app.app_context():
        try:
            from alembic.config import Config
            from alembic.script import ScriptDirectory
            from alembic.runtime.migration import MigrationContext
            import os

            # Get path to migrations directory
            migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
            alembic_cfg = Config(os.path.join(migrations_dir, 'alembic.ini'))
            alembic_cfg.set_main_option('script_location', migrations_dir)

            script = ScriptDirectory.from_config(alembic_cfg)

            # Get current revision
            with db.engine.connect() as connection:
                context = MigrationContext.configure(connection)
                current_rev = context.get_current_revision()

            # Get head revision
            head_rev = script.get_current_head()

            return current_rev != head_rev, current_rev, head_rev
        except Exception as e:
            print(f"Error checking migrations: {e}")
            return None, None, None


def init_db():
    """Initialize database with migrations"""
    app = create_app()

    print("=" * 60)
    print("Database Initialization")
    print("=" * 60)

    # Check database connection
    print("\n1. Checking database connection...")
    try:
        with app.app_context():
            db.engine.connect()
            print("   ✓ Database connection successful")
    except Exception as e:
        print(f"   ✗ Database connection failed: {e}")
        return False

    # Check if alembic_version table exists
    print("\n2. Checking migration status...")
    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(db.engine)

        if 'alembic_version' not in inspector.get_table_names():
            print("   → No migrations found. Running initial setup...")
            try:
                upgrade()
                print("   ✓ Database initialized successfully")
            except Exception as e:
                print(f"   ✗ Migration failed: {e}")
                return False
        else:
            # Check for pending migrations
            needs_migration, current_rev, head_rev = check_migrations_needed()

            if needs_migration is None:
                print("   ✗ Could not check migration status")
                return False
            elif needs_migration:
                print(f"   → Current revision: {current_rev or 'none'}")
                print(f"   → Head revision: {head_rev}")
                print("   → Pending migrations found. Running upgrade...")
                try:
                    upgrade()
                    print("   ✓ Database upgraded successfully")
                except Exception as e:
                    print(f"   ✗ Migration failed: {e}")
                    return False
            else:
                print("   ✓ Database is up to date")

    print("\n" + "=" * 60)
    print("Database ready!")
    print("=" * 60)
    return True


def show_status():
    """Show current database status"""
    app = create_app()

    print("=" * 60)
    print("Database Status")
    print("=" * 60)

    with app.app_context():
        try:
            # Database info
            print(f"\nDatabase URL: {db.engine.url}")
            print(f"Dialect: {db.engine.dialect.name}")

            # Current revision
            from alembic.config import Config
            from alembic.script import ScriptDirectory
            from alembic.runtime.migration import MigrationContext
            import os

            # Get path to migrations directory
            migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
            alembic_cfg = Config(os.path.join(migrations_dir, 'alembic.ini'))
            alembic_cfg.set_main_option('script_location', migrations_dir)

            script = ScriptDirectory.from_config(alembic_cfg)

            with db.engine.connect() as connection:
                context = MigrationContext.configure(connection)
                current_rev = context.get_current_revision()

            head_rev = script.get_current_head()

            print(f"\nCurrent Revision: {current_rev or 'None'}")
            print(f"Head Revision: {head_rev}")

            if current_rev == head_rev:
                print("\n✓ Database is up to date")
            else:
                print("\n⚠ Pending migrations found!")
                print("  Run: flask db upgrade")

            # Table count
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"\nTables ({len(tables)}): {', '.join(tables)}")

        except Exception as e:
            print(f"\n✗ Error: {e}")

    print("\n" + "=" * 60)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Database management script')
    parser.add_argument('command', choices=['init', 'status', 'create-db', 'seed'],
                        help='Command to execute')

    args = parser.parse_args()

    if args.command == 'create-db':
        print("Creating database...")
        if create_database_if_not_exists():
            print("✓ Done")
        else:
            print("✗ Failed")
            sys.exit(1)
    elif args.command == 'init':
        if not init_db():
            sys.exit(1)
    elif args.command == 'status':
        show_status()
    elif args.command == 'seed':
        print("Seeding database with initial data...")
        try:
            seed_database()
            print("✓ Seeding complete")
        except Exception as e:
            print(f"✗ Seed failed: {e}")
            sys.exit(1)
