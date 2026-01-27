from app.models import Genre, Book, Author
from app import create_app, db
from flask import session
import os
from dotenv import load_dotenv

# Load environment variables from .env file BEFORE importing app
load_dotenv()


app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {
        "db": db,
        "Book": Book,
        "Author": Author,
        "Genre": Genre,
        "session": session,
    }


if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug_mode)
