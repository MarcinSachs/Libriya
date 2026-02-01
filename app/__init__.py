from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_babel import _, Babel, lazy_gettext as _l
from flask import session, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
babel = Babel()
limiter = Limiter(key_func=get_remote_address)
csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)

    # Initialize Pydantic Settings instance and update Flask config
    config = config_class()
    app.config.update(config.model_dump())

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    # Ustaw komunikat logowania z tłumaczeniem dynamicznym
    login_manager.login_message = _l("Please log in to access this page.")
    limiter.init_app(app)
    csrf.init_app(app)

    def get_locale():
        # 1. Check for language in cookie first
        lang = request.cookies.get("language")
        if lang and lang in app.config["LANGUAGES"]:
            return lang

        # 2. Check session for backward compatibility
        lang = session.get("language")
        if lang and lang in app.config["LANGUAGES"]:
            return lang

        # 3. Fallback to browser's preferred language
        best_lang = request.accept_languages.best_match(app.config["LANGUAGES"])
        return best_lang or app.config["BABEL_DEFAULT_LOCALE"]

    babel.init_app(app, locale_selector=get_locale)

    # Register all blueprints
    from app.routes import register_blueprints
    register_blueprints(app)

    # Add security headers
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = (
            'max-age=31536000; includeSubDomains'
        )
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net https://fonts.googleapis.com https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net "
            "https://fonts.googleapis.com https://unpkg.com; "
            "font-src 'self' https://fonts.gstatic.com https://unpkg.com; "
            "img-src 'self' data: https:;"
        )

        # Allow Service Worker to control entire site from /static/ folder
        if request.path.endswith('service-worker.js'):
            response.headers['Service-Worker-Allowed'] = '/'

        return response

    # Register CLI commands
    register_cli_commands(app)

    # Initialize background scheduler for periodic cleanup
    from app.utils.scheduler import init_scheduler, shutdown_scheduler
    init_scheduler(app)

    # Shutdown scheduler on app teardown
    app.teardown_appcontext(lambda exc=None: shutdown_scheduler())

    return app


def register_cli_commands(app):
    """Register Flask CLI commands"""
    import click
    from datetime import datetime, timedelta

    @app.cli.command('cleanup-notifications')
    @click.option('--days', default=30, help='Delete notifications older than X days (default: 30)')
    def cleanup_notifications(days):
        """Delete old read notifications to avoid database bloat"""
        from app.models import Notification

        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted_count = Notification.query.filter(
            Notification.is_read == True,
            Notification.timestamp < cutoff_date
        ).delete()

        db.session.commit()
        click.echo(f'Deleted {deleted_count} old notifications (older than {days} days)')


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))
