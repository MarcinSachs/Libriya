#!/usr/bin/env python
"""Bootstrap script for fresh production installs.

This script can be uploaded to the server together with the repository and
run once after the environment variables have been configured.  It uses
real process environment variables; a `.env.production` file is only loaded
if present and is treated as a convenience for development or container
images.  On hosts where you set `DATABASE_URL`, `SECRET_KEY`, etc. in the
system or orchestration layer, you can omit the file entirely.

The script will:

1. load the environment file (if it exists)
2. create the database if it doesn't exist (MySQL/MariaDB)
3. apply all pending migrations / initialize schema
4. seed the database with the default tenant, library, superadmin, genres, etc.

It reuses the helpers already defined in ``manage_db.py``.

Usage::

    python scripts/setup_server.py

The file is idempotent; running it multiple times is harmless as each step
checks before acting.
"""


import os
import sys

from dotenv import load_dotenv

# make sure script can import the package even if cwd==scripts/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# attempt to import helpers; if a dependency is missing, try to install it
try:
    from scripts.manage_db import (
        create_database_if_not_exists,
        init_db,
        seed_database,
    )
except ModuleNotFoundError as exc:
    missing = str(exc).split()[-1].strip("'\n")
    print(f"\nERROR: missing module {missing}. Attempting to install...")
    # only attempt for our known dependency; otherwise show message
    if missing in ('pydantic_settings', 'pydantic-settings'):
        try:
            import subprocess
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', missing])
            # try import again
            from scripts.manage_db import (
                create_database_if_not_exists,
                init_db,
                seed_database,
            )
            print("Successfully installed missing package.")
        except Exception as install_exc:
            print(f"Automatic install failed: {install_exc}")
            print("Please run pip install -r requirements.txt in the virtualenv.")
            sys.exit(1)
    else:
        print(exc)
        print("Make sure you've installed the Python dependencies, e.g.:\n    python -m pip install -r requirements.txt")
        sys.exit(1)


def _strip_quotes(varname: str):
    """Remove surrounding single/double quotes from an env var if present."""
    val = os.getenv(varname)
    if val and ((val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'"))):
        os.environ[varname] = val[1:-1]


def main():
    # If the hosting control panel stored quotes literally, clean them up
    for key in ('MAIL_USERNAME', 'MAIL_DEFAULT_SENDER'):
        _strip_quotes(key)

    # load production environment variables (file name hardcoded here;
    # in a container you might load something from env directly)
    env_file = os.getenv('ENV_FILE', '.env.production')
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print(f"Loaded environment from {env_file}")
    else:
        print(f"Environment file {env_file} not found, relying on existing env vars")

    # Step 1: create database (if using MySQL/MariaDB)
    print("\n[1] creating database if it does not exist...")
    if not create_database_if_not_exists():
        print("error: failed to create database")
        sys.exit(1)

    # Step 2: run migrations / create schema
    print("\n[2] initialising / upgrading schema...")
    if not init_db():
        print("error: migration/initialisation failed")
        sys.exit(1)

    # Step 3: seed default data (superadmin, tenant, genres...)
    print("\n[3] seeding database with default records...")
    try:
        seed_database()
    except Exception as e:
        print(f"seeding failed: {e}")
        sys.exit(1)

    print("\nsetup complete. you may now start the application server.")


if __name__ == '__main__':
    main()
