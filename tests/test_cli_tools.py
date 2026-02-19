import subprocess
import sys
import os

def test_check_migrations_runs():
    script = os.path.join('scripts', 'check_migrations.py')
    result = subprocess.run([sys.executable, script], capture_output=True, text=True)
    if result.returncode != 0:
        print('STDOUT:', result.stdout)
        print('STDERR:', result.stderr)
    assert result.returncode == 0 or result.returncode is None

def test_reset_migrations_runs():
    script = os.path.join('scripts', 'reset_migrations.py')
    # Only run if not in production
    os.environ['FLASK_ENV'] = 'development'
    result = subprocess.run([sys.executable, script], capture_output=True, text=True)
    if result.returncode != 0:
        print('STDOUT:', result.stdout)
        print('STDERR:', result.stderr)
    assert result.returncode == 0 or result.returncode is None
