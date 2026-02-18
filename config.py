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

    # Caching configuration
    CACHE_TYPE: str = 'SimpleCache'  # in-memory cache suitable for single-server deployments
    CACHE_DEFAULT_TIMEOUT: int = 3600  # 1 hour (can be overridden per cache key)
    CACHE_TENANT_TIMEOUT: int = 3600  # Cache tenant lookups for 1 hour
    CACHE_PREMIUM_FEATURES_TIMEOUT: int = 3600  # Cache premium features for 1 hour
    CACHE_USER_TIMEOUT: int = 1800  # Cache user lookups for 30 minutes

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False
        extra = 'ignore'  # Ignore extra fields from .env
