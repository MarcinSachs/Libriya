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

if __name__ == '__main__':
    app.run(debug=True)
