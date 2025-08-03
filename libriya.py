from app import create_app, db
from app.models import Genre, Book, Author

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {
        "db": db,
        "Book": Book,
        "Author": Author,
        "Genre": Genre,
    }


@app.context_processor
def inject_current_user():
    """
    Injects the current user into all templates.
    NOTE: This is a placeholder. In a real application, you would get
    the user from the session (e.g., using Flask-Login).
    """
    # For now, we'll just get the first user as an example.
    from app.models import User
    user = db.session.query(User).first()
    return dict(current_user=user)


if __name__ == '__main__':
    app.run(debug=True)
