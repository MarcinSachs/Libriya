from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_babel import Babel
from flask import current_app, session, request

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'main.login'
babel = Babel()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    def get_locale():
        # 1. Check for language in cookie first
        lang = request.cookies.get("language")
        if lang and lang in app.config["LANGUAGES"]:
            current_app.logger.debug(
                f"Locale selector: found language in cookie: {lang}")
            return lang

        # 2. Check session for backward compatibility (can be removed later)
        lang = session.get("language")
        if lang and lang in app.config["LANGUAGES"]:
            current_app.logger.debug(
                f"Locale selector: found language in session: {lang}")
            return lang

        # 3. Fallback to browser's preferred language
        browser_lang = request.accept_languages.best_match(
            app.config["LANGUAGES"])
        current_app.logger.debug(
            f"Locale selector: falling back to browser language: {browser_lang}"
        )
        return browser_lang

    babel.init_app(app, locale_selector=get_locale)

    from app.routes import bp as main_blueprint
    app.register_blueprint(main_blueprint)

    from app import models

    return app


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))
