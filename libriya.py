from flask import session
from app.models import Genre, Book, Author
from app import create_app, db
import os

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

    # Enable HTTPS for camera access on mobile devices
    # Using adhoc SSL context (self-signed certificate)
    app.run(host="0.0.0.0", port=5000, debug=debug_mode, ssl_context='adhoc')
