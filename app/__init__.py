
from flask import Flask, request, current_app
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_babel import Babel

db = SQLAlchemy()
migrate = Migrate()

def get_locale_selector_function():
    if 'lang' in request.args:
        if request.args['lang'] in current_app.config.get('LANGUAGES', []): # Użyj .get z domyślną wartością dla bezpieczeństwa
            return request.args['lang']
    lang_cookie = request.cookies.get('lang')
    if lang_cookie and lang_cookie in current_app.config.get('LANGUAGES', []):
        return lang_cookie
    return request.accept_languages.best_match(current_app.config.get('LANGUAGES', []))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    from app.routes import bp as main_blueprint
    app.register_blueprint(main_blueprint)

    login_manager = LoginManager()
    login_manager.login_view = 'main.login'
    login_manager.init_app(app)

    babel = Babel(app)
    app.config['BABEL_LOCALE_SELECTOR'] = get_locale_selector_function


    from app import models

    @login_manager.user_loader
    def load_user(user_id):
        # since the user_id is just the primary key of our user table, use it in the query for the user
        from app.models import User
        return User.query.get(int(user_id))

    return app
