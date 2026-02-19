import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from libriya import create_app
app = create_app()
with app.app_context():
    print('SQLALCHEMY_DATABASE_URI=', app.config.get('SQLALCHEMY_DATABASE_URI'))
    db_path = None
    uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    if uri and uri.startswith('sqlite:'):
        # extract file path
        if uri == 'sqlite:///:memory:':
            print('Using in-memory DB')
        else:
            # handle sqlite:///relative/path.db or sqlite:////absolute
            path = uri.replace('sqlite:///', '')
            print('resolved path ->', path)
            exists = os.path.exists(os.path.join(os.getcwd(), path))
            print('exists at project cwd?', exists)
            abs_path = os.path.abspath(path)
            print('abs path', abs_path, 'exists?', os.path.exists(abs_path))
    # list files in workspace root
    print('\nWorkspace files:')
    for f in os.listdir(os.getcwd()):
        print(' -', f)
