import os
from pydantic_settings import BaseSettings
from pydantic import model_validator
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
    UPLOAD_FOLDER: str = os.path.join(BASE_DIR, 'app/static/uploads')

    # Internationalization
    LANGUAGES: list = ['en', 'pl']
    BABEL_DEFAULT_LOCALE: str = 'en'
    BABEL_DEFAULT_TIMEZONE: str = 'UTC'
    BABEL_TRANSLATION_DIRECTORIES: str = os.path.join(BASE_DIR, 'translations')

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False
        extra = 'ignore'  # Ignore extra fields from .env
