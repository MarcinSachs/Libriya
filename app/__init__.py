from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_babel import _, Babel, lazy_gettext as _l
from flask import session, request, render_template, flash, redirect, url_for, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache
from markupsafe import Markup

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
babel = Babel()
limiter = Limiter(key_func=get_remote_address)
csrf = CSRFProtect()
cache = Cache()


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

    # Initialize Limiter with environment-based storage (Opcja 1)
    # Development: uses memory:// (SimpleCache)
    # Production: uses Redis if RATELIMIT_STORAGE_URL is set
    storage_url = app.config.get('RATELIMIT_STORAGE_URL')
    if storage_url:
        # flask-limiter now expects the URI to live in config key
        # `RATELIMIT_STORAGE_URI`.  Copy the value over and call init_app
        app.config['RATELIMIT_STORAGE_URI'] = storage_url
    # always call init_app without extra args; configuration is read from app.config
    limiter.init_app(app)

    csrf.init_app(app)
    cache.init_app(app)

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

    # Register custom Jinja2 filters
    def linebreaksbr(text):
        """Convert line breaks to HTML <br> tags"""
        if text is None:
            return ""
        return Markup(str(text).replace('\n', '<br>\n').replace('\r', ''))

    app.jinja_env.filters['linebreaksbr'] = linebreaksbr

    # Helper function to get tenant from subdomain
    def get_tenant_from_subdomain():
        """Extract tenant from subdomain if present"""
        from flask import request
        from app.services.cache_service import get_tenant_by_subdomain_cached

        host = request.host.split(':')[0]  # Remove port
        host_parts = host.split('.')

        # Check if it's a subdomain (not localhost or www)
        if len(host_parts) > 1 and host_parts[0] not in ('localhost', 'www', '127'):
            subdomain = host_parts[0]
            tenant = get_tenant_by_subdomain_cached(subdomain)
            return tenant
        return None

    # Make it available in Flask app context
    app.get_tenant_from_subdomain = get_tenant_from_subdomain

    # Initialize premium features manager
    from app.services.premium.manager import PremiumManager
    PremiumManager.init()

    # Register all blueprints
    from app.routes import register_blueprints
    register_blueprints(app)

    # Register multi-tenant middleware
    @app.before_request
    def enforce_https():
        """Enforce HTTPS in production by redirecting HTTP requests"""
        # Only enforce in production and when not running in debug mode
        if (not app.debug and
            not request.is_secure and
            request.headers.get('X-Forwarded-Proto', 'http') == 'http' and
                app.config.get('HTTPS_REDIRECT', True)):
            # Redirect HTTP to HTTPS
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)

    @app.before_request
    def handle_tenant_routing():
        """
        Handle tenant-specific routing logic.

        For subdomain-based tenants:
        - If authenticated user accesses '/', redirect to home/dashboard
        - If unauthenticated user accesses non-auth pages, redirect to login
        """
        from flask_login import current_user
        from app.services.cache_service import get_tenant_by_subdomain_cached

        # Allow static files and logout for everyone
        if request.path.startswith('/static') or request.path == '/auth/logout':
            return

        # Get tenant from subdomain
        host_parts = request.host.split(':')[0].split('.')
        tenant = None

        if len(host_parts) > 1 and host_parts[0] not in ('localhost', 'www', '127'):
            subdomain = host_parts[0]
            try:
                tenant = get_tenant_by_subdomain_cached(subdomain)
            except Exception as e:
                # Log error but don't break the request if database is unavailable
                app.logger.debug(f"Error fetching tenant for subdomain '{subdomain}': {e}")
                tenant = None

        # Tenant-specific routing logic
        if tenant:
            # 1. If authenticated user tries to access landing page on subdomain, redirect to home
            if current_user.is_authenticated and request.endpoint == 'main.landing':
                return redirect(url_for('main.home'))

            # 2. If NOT authenticated and NOT on auth/static pages, redirect to login
            # List of allowed endpoints for unauthenticated users on subdomain
            allowed_endpoints = [
                'auth.login',
                'auth.register',
                'auth.register_choice',
                'auth.password_reset',
                'auth.password_reset_confirm',
                'auth.verify_email',
                'auth.verify_email_send',
                'static'
            ]

            if not current_user.is_authenticated and request.endpoint not in allowed_endpoints:
                return redirect(url_for('auth.login'))

    @app.before_request
    def verify_tenant_access():
        """
        Middleware sprawdzający dostęp do tenantu
        Zapobiega dostępowi do innego tenantu
        Zapobiega super-adminowi dostępu do normalnych stron (tylko /admin/*)
        Inicjalizuje PremiumContext dla zalogowanego użytkownika
        """
        from flask_login import current_user
        from app.services.premium.context import PremiumContext

        # Inicjalizuj PremiumContext dla zalogowanego użytkownika
        if current_user.is_authenticated and current_user.tenant_id:
            try:
                # Tenant user - załaduj premium features dla jego tenantu (z cache)
                from app.services.cache_service import get_premium_features_cached
                enabled_features = get_premium_features_cached(current_user.tenant_id)
                PremiumContext.set_for_tenant(current_user.tenant_id, enabled_features)
                # Set to g for template access
                g.premium_features = enabled_features
            except Exception as e:
                # If database is unavailable, just set empty context
                app.logger.debug(f"Error loading premium features: {e}")
                PremiumContext.set_for_tenant(None, set())
                g.premium_features = set()
        else:
            # Super-admin - super-admini mają dostęp do wszystkich features globalnie
            PremiumContext.set_for_tenant(None, set())  # No specific tenant context
            g.premium_features = set()

        # Pozwól na static files i logout dla wszystkich
        if request.path.startswith('/static') or request.path == '/auth/logout':
            return

        # Super-admin ma dostęp TYLKO do /admin, /admin/*, /messaging/admin/*,
        # oraz stron potrzebnych do zarządzania kontem: powiadomień i ustawień.
        if current_user.is_authenticated and current_user.is_super_admin:
            if (
                request.path == '/admin' or
                request.path.startswith('/admin/') or
                request.path.startswith('/messaging/admin') or
                request.path.startswith('/notifications') or
                request.path.startswith('/user/settings') or
                request.path == '/auth/logout'
            ):
                return  # Pozwól
            else:
                from flask import abort
                abort(403)  # Zabroń dostępu poza dozwoloną listę

        # Pobierz tenant z subdomeny (z cache)
        try:
            host_parts = request.host.split(':')[0].split('.')
            if len(host_parts) > 1 and host_parts[0] not in ('localhost', 'www', '127'):
                subdomain = host_parts[0]
                from app.services.cache_service import get_tenant_by_subdomain_cached
                tenant = get_tenant_by_subdomain_cached(subdomain)

                # If the current_user is logged in, ensure their tenant subdomain matches the request subdomain
                if current_user.is_authenticated and getattr(current_user, 'tenant_id', None):
                    try:
                        from app.services.cache_service import get_tenant_by_id_cached
                        current_tenant = get_tenant_by_id_cached(current_user.tenant_id)
                    except Exception:
                        current_tenant = None
                    if current_tenant and current_tenant.subdomain != subdomain:
                        from flask import abort
                        abort(403)

                # Also check session-based user id for tests where Flask-Login may not be populated
                session_user_id = session.get('_user_id')
                if session_user_id:
                    try:
                        session_user_id_int = int(session_user_id)
                    except Exception:
                        session_user_id_int = None
                    if session_user_id_int:
                        from app.models import User as AppUser
                        session_user = AppUser.query.get(session_user_id_int)
                        if session_user and session_user.tenant_id and tenant and session_user.tenant_id != tenant.id:
                            from flask import abort
                            abort(403)

                # Jeśli subdomena nie istnieje - zwróć 404 tylko gdy ENFORCE_SUBDOMAIN_EXISTS=True
                if not tenant:
                    if app.config.get('ENFORCE_SUBDOMAIN_EXISTS', True):
                        from flask import abort
                        abort(404)
                    # else: allow unknown subdomains (development/local use)

                # Sprawdź czy użytkownik należy do tego tenantu
                if current_user.is_authenticated and tenant and current_user.tenant_id != tenant.id:
                    from flask import abort
                    abort(403)  # Forbidden
        except Exception as e:
            # Log error but don't break the request if database is unavailable
            # This allows the app to continue working even if the database is temporarily down
            app.logger.debug(f"Error in verify_tenant_access: {e}")

    # Add security headers
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # Only use HSTS in production (not development/local testing)
        if not app.debug:
            response.headers['Strict-Transport-Security'] = (
                'max-age=31536000; includeSubDomains'
            )

        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' "
            "https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://fonts.googleapis.com https://unpkg.com https://storage.googleapis.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://cdn.jsdelivr.net "
            "https://fonts.googleapis.com https://unpkg.com; "
            "font-src 'self' https://fonts.gstatic.com https://unpkg.com; "
            "img-src 'self' data: https:;"
        )

        # Allow Service Worker to control entire site from /static/ folder
        if request.path.endswith('service-worker.js'):
            response.headers['Service-Worker-Allowed'] = '/'

        return response

    # Global PWA context (applies to all blueprints/templates)
    @app.context_processor
    def inject_global_pwa_settings():
        return {
            'PWA_CACHE_VERSION': app.config.get('PWA_CACHE_VERSION', 'v1'),
            'PWA_PRECACHE_PAGES': app.config.get('PWA_PRECACHE_PAGES', []),
            'PWA_UPDATE_INTERVAL': app.config.get('PWA_UPDATE_INTERVAL', 300000),
        }

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 errors"""
        flash(_('You do not have permission to access this page'), 'danger')
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        db.session.rollback()
        app.logger.error(f'Server error: {error}')
        return render_template('errors/500.html'), 500

    @app.errorhandler(429)
    def ratelimit_handler(e):
        """Handle rate limit exceeded"""
        flash(_('Too many requests. Please try again later.'), 'danger')
        return redirect(request.referrer or url_for('main.home')), 429

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
    from app.services.cache_service import get_user_by_id_cached
    user = get_user_by_id_cached(int(user_id))
    # _get_user_cached already merges into the session, but do an extra safety
    # merge here to be sure any calling code always gets an attached instance.
    if user is not None:
        try:
            return db.session.merge(user)
        except Exception:
            return user
    return None
