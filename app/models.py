from app import db


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(13), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey(
        'author.id'), nullable=False)
    genre_id = db.Column(db.Integer, db.ForeignKey(
        'genre.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    cover = db.Column(db.String(200))
    is_available = db.Column(db.Boolean, default=True)

    def __str__(self):
        return f"{self.title} by {self.author.name} ({self.year})"


class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    books = db.relationship('Book', backref='author', lazy=True)

    def __str__(self):
        return self.name


class Genre(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, index=True)
    books = db.relationship('Book', backref='genre', lazy=True)

    def __str__(self):
        return self.name
