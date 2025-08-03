from app import db
from werkzeug.security import generate_password_hash, check_password_hash


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


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True,
                         nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)

    def __str__(self):
        return self.username

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    loan_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    return_date = db.Column(db.DateTime)

    book = db.relationship('Book', backref='loans')
    user = db.relationship('User', backref='loans')

    def __str__(self):
        return f"{self.user.username} borrowed {self.book.title}"
