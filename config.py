import os
from pydantic_settings import BaseSettings
from pydantic import model_validator, field_validator
from typing import Any, Optional

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DB_URI = f'sqlite:///{os.path.join(BASE_DIR, "libriya.db")}'


class Config(BaseSettings):
    # Security configuration
    SECRET_KEY: str

    # Database
    DATABASE_URL: str = DEFAULT_DB_URI
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {}

    # Email settings
    MAIL_SERVER: Optional[str] = None
    MAIL_PORT: Optional[int] = None
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_USE_TLS: bool = False
    MAIL_USE_SSL: bool = False
    MAIL_DEFAULT_SENDER: Optional[str] = None

    # Audit retention (days)
    AUDIT_RETENTION_DAYS: int = 30

    @model_validator(mode='after')
    def set_database_config(self) -> 'Config':
        """Set SQLALCHEMY_DATABASE_URI from DATABASE_URL and configure engine options"""
        # Set SQLALCHEMY_DATABASE_URI to match DATABASE_URL
        self.SQLALCHEMY_DATABASE_URI = self.DATABASE_URL

        # Configure engine options based on database type
        if 'mysql' in self.DATABASE_URL or 'mariadb' in self.DATABASE_URL:
            self.SQLALCHEMY_ENGINE_OPTIONS = {
                'pool_size': 10,
                'pool_recycle': 3600,
                'pool_pre_ping': True,
                'max_overflow': 20,
                'connect_args': {
                    'charset': 'utf8mb4',
                }
            }

        return self

    # File upload
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16MB max request size

    @field_validator('MAX_CONTENT_LENGTH', mode='before')
    def _parse_max_content_length(cls, v):
        """Allow MAX_CONTENT_LENGTH to be specified in .env with inline comments like '16777216  # 16MB in bytes'.
        Strip comments and whitespace before parsing to int.
        """
        if v is None:
            return v
        if isinstance(v, str):
            # Remove anything after a '#' (inline comment) and strip
            v = v.split('#', 1)[0].strip()
        try:
            return int(v)
        except Exception:
            # Fallback to default if parsing fails
            return 16 * 1024 * 1024

    UPLOAD_FOLDER: str = os.path.join(BASE_DIR, 'app/static/uploads')

    # Internationalization
    LANGUAGES: list = ['en', 'pl']
    BABEL_DEFAULT_LOCALE: str = 'en'
    BABEL_DEFAULT_TIMEZONE: str = 'UTC'
    BABEL_TRANSLATION_DIRECTORIES: str = os.path.join(BASE_DIR, 'translations')

    # Premium Features (optional - defaults to disabled for safety)
    PREMIUM_BOOKCOVER_ENABLED: bool = False
    PREMIUM_BIBLIOTEKA_NARODOWA_ENABLED: bool = False

    # Enforce whether requests to unknown subdomains should return 404.
    # Set to False during local development if you use custom hosts or wildcard domains.
    ENFORCE_SUBDOMAIN_EXISTS: bool = True

    # HTTPS Configuration
    HTTPS_REDIRECT: bool = False  # Set to False for development without HTTPS

    # Caching configuration
    CACHE_TYPE: str = 'SimpleCache'  # in-memory cache suitable for single-server deployments
    CACHE_DEFAULT_TIMEOUT: int = 3600  # 1 hour (can be overridden per cache key)
    CACHE_TENANT_TIMEOUT: int = 3600  # Cache tenant lookups for 1 hour
    CACHE_PREMIUM_FEATURES_TIMEOUT: int = 3600  # Cache premium features for 1 hour
    CACHE_USER_TIMEOUT: int = 1800  # Cache user lookups for 30 minutes

    # Progressive Web App (PWA) settings
    # Version string used for cache names; bumping this forces the service worker
    # to remove old caches automatically.  Set via environment or defaults to 'v5'.
    # Increment this value whenever the service worker or caching logic changes
    # in a way that should invalidate existing client-side caches.
    PWA_CACHE_VERSION: str = 'v5'

    # Interval (milliseconds) at which the client will call
    # ``serviceWorker.update()`` when online.  Longer intervals reduce churn in
    # development environments and lighten network traffic.
    PWA_UPDATE_INTERVAL: int = 300000  # 5 minutes

    # Pages that the client-side pre-cache routine should download when the
    # user explicitly asks for offline data (via the settings UI).  These URLs
    # may require authentication and are **not** automatically precached by the
    # service worker on install; the SW template filters out protected paths.
    PWA_PRECACHE_PAGES: list = ['/', '/loans/', '/libraries/',
                                '/users/', '/notifications/', '/user/settings', '/offline']

    # Application environment: development | staging | production
    APP_ENV: str = os.getenv('FLASK_ENV', 'development')

    # Rate Limiter Storage Configuration (Opcja 1: Development bez Redisa, Production z Redisem)
    # Development: uses in-memory store (SimpleCache)
    # Production: uses Redis (must be configured via RATELIMIT_STORAGE_URL env var)
    RATELIMIT_STORAGE_URL: Optional[str] = os.getenv('RATELIMIT_STORAGE_URL', None)

    # Session and cookie security (critical for production).
    # `SESSION_COOKIE_SECURE` is set to False by default to allow HTTP during
    # local development. A production deployment **must** override it to True
    # (via environment or APP_ENV) as browsers will then omit the cookie over
    # plain HTTP.
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SECURE: bool = False  # automatically promoted in production
    SESSION_COOKIE_SAMESITE: str = 'Lax'  # Prevent CSRF attacks
    PERMANENT_SESSION_LIFETIME: int = 3600  # 1 hour session timeout

    # Have I Been Pwned (HIBP) / pwned-passwords settings
    # Disabled by default for safety; config controls enabling only in production.
    ENABLE_PWNED_CHECK: bool = False
    HIBP_TIMEOUT: float = 5.0
    HIBP_CACHE_TTL: int = 86400  # 24 hours in seconds

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False
        extra = 'ignore'  # Ignore extra fields from .env

        @model_validator(mode='after')
        def enforce_hibp_production_only(self) -> 'Config':
            """Ensure HIBP checks are only enabled in production by default.

            - If `APP_ENV` is not 'production', force `ENABLE_PWNED_CHECK` to False to
                avoid accidental outbound requests in development/testing.
            - If `APP_ENV` is 'production' and the environment didn't explicitly set
                `ENABLE_PWNED_CHECK`, enable it by default (safe production opt-in).
            """
            env = getattr(self, 'APP_ENV', None) or os.getenv('FLASK_ENV') or 'development'
            self.APP_ENV = env
            # Adjust cookie security automatically
            if env.lower() != 'production':
                # never send 'Secure' on non-HTTPS, avoids missing session
                self.SESSION_COOKIE_SECURE = False
            else:
                # in production default to True unless explicitly disabled
                if 'SESSION_COOKIE_SECURE' not in os.environ:
                    self.SESSION_COOKIE_SECURE = True
            # If not running in production, always disable HIBP checks regardless of .env
            if env.lower() != 'production':
                self.ENABLE_PWNED_CHECK = False
                return self

            # Running in production: if the operator explicitly set ENABLE_PWNED_CHECK
            # in the environment, respect it; otherwise enable by default in prod.
            if 'ENABLE_PWNED_CHECK' in os.environ:
                # pydantic already loaded the env value into self.ENABLE_PWNED_CHECK
                return self

            # No explicit env value: enable in production by default
            self.ENABLE_PWNED_CHECK = True
            return self
