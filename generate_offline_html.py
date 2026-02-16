# Skrypt do generowania static/offline.html na podstawie szablonu Flask
# Uruchom: python generate_offline_html.py

from types import SimpleNamespace
from flask import Flask, render_template
import os


app = Flask(__name__, template_folder="app/templates")
app.config['SECRET_KEY'] = 'offline-render'
app.config['SERVER_NAME'] = 'localhost:5000'  # Needed for url_for outside request

# Dummy translation function for offline rendering


def _(text):
    return text


app.jinja_env.globals['_'] = _

# Dummy current_user for offline rendering (not authenticated)
app.jinja_env.globals['current_user'] = SimpleNamespace(is_authenticated=False)

# Import blueprintów i konfiguracji jeśli potrzebne
# from app import create_app
# app = create_app()

with app.app_context():
    with app.test_request_context('/'):
        html = render_template('base/offline.html', title='Offline')
        static_path = os.path.join(os.path.dirname(__file__), 'app', 'static', 'offline.html')
        with open(static_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'Wygenerowano: {static_path}')
