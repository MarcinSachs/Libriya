import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # SECRET_KEY must be set via environment variable for security
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError(
            "CRITICAL: SECRET_KEY environment variable is not set! "
            "Set it before running the application: export SECRET_KEY='your-secret-key'"
        )

    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL') or
        ('sqlite:///' + os.path.join(BASE_DIR, 'libriya.db'))
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max request size
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app/static/uploads')

    # Internationalization
    LANGUAGES = ['en', 'pl']
    BABEL_DEFAULT_LOCALE = 'pl'
    BABEL_DEFAULT_TIMEZONE = 'UTC'
    BABEL_TRANSLATION_DIRECTORIES = os.path.join(BASE_DIR, 'translations')
