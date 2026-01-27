import os
from pydantic_settings import BaseSettings

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_DB_URI = f'sqlite:///{os.path.join(BASE_DIR, "libriya.db")}'


class Config(BaseSettings):
    # Security configuration
    SECRET_KEY: str

    # Database
    DATABASE_URL: str = DEFAULT_DB_URI
    SQLALCHEMY_DATABASE_URI: str = DEFAULT_DB_URI
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

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
