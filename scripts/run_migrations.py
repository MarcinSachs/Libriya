# run_migrations.py
"""Helper that runs the migration helper from anywhere.

This script is intended for use by hosting panels that execute a named
Python file but have no guarantee what their current working directory is.
We mimic ``scripts/setup_server.py`` by prepending the project root to
``sys.path`` so that ``import app`` and ``import scripts.manage_db`` work.
"""

import os
import sys

# ensure project root (one level up from this file) is on sys.path
proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, proj_root)

# now we can safely import helpers from our package
from scripts.manage_db import init_db
if not init_db():
    sys.exit(1)
