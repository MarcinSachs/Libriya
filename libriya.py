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

    # For ngrok: use SSL context if available
    ssl_context = None
    if os.environ.get('USE_SSL', 'false').lower() == 'true':
        try:
            ssl_context = 'adhoc'
            print("🔒 Running with HTTPS (adhoc SSL) for ngrok compatibility")
        except Exception as e:
            print(f"⚠️  SSL not available: {e}")
            print("   Install with: pip install pyopenssl cryptography")

    # Run Flask
    app.run(host="0.0.0.0", port=5000, debug=debug_mode, ssl_context=ssl_context)
