from flask import session
from app.models import Genre, Book, Author
from app import create_app, db
import os
from dotenv import load_dotenv

# Load environment variables BEFORE creating app
load_dotenv('.env')

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

    # Run on HTTP (use Ngrok for HTTPS in development)
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
