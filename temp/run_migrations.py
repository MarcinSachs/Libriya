import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from libriya import create_app
from flask_migrate import upgrade

app = create_app()

with app.app_context():
    print('Running migrations via Flask-Migrate...')
    upgrade()
    print('Migrations complete.')
