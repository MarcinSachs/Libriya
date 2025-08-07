from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import datetime


# Define the association table for book-author relationship
book_authors = db.Table('book_authors',
                        db.Column('book_id', db.Integer, db.ForeignKey(
                            'book.id'), primary_key=True),
                        db.Column('author_id', db.Integer, db.ForeignKey(
                            'author.id'), primary_key=True)
                        )
# Define the association table for book-genre relationship (NEW)
book_genres = db.Table('book_genres',
                        db.Column('book_id', db.Integer, db.ForeignKey(
                            'book.id'), primary_key=True),
                        db.Column('genre_id', db.Integer, db.ForeignKey(
                            'genre.id'), primary_key=True)
                        )

# Define the association table for favorites
favorites = db.Table('favorites',
                     db.Column('user_id', db.Integer, db.ForeignKey(
                         'user.id'), primary_key=True),
                     db.Column('book_id', db.Integer, db.ForeignKey(
                         'book.id'), primary_key=True)
                     )


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(13), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    authors = db.relationship(
        'Author', secondary=book_authors, lazy='subquery', back_populates='books')
    
    #Relationship for multiple genres
    genres = db.relationship(
        'Genre', secondary=book_genres, lazy='subquery', back_populates='books')
    
    year = db.Column(db.Integer, nullable=False)
    cover = db.Column(db.String(200))
    # 'available', 'reserved', 'on_loan'
    status = db.Column(db.String(50), default='available', nullable=False)

    comments = db.relationship('Comment', back_populates='book', lazy=True, cascade='all, delete-orphan')

    def __str__(self):
        author_names = ", ".join([author.name for author in self.authors])
        genre_names = ", ".join([genre.name for genre in self.genres])
        return f"{self.title} by {author_names} ({self.year}) - Genres: {genre_names}"


class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    books = db.relationship('Book', secondary=book_authors,
                            lazy='subquery', back_populates='authors')

    def __str__(self):
        return self.name


class Genre(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, index=True)
    books = db.relationship('Book', secondary=book_genres,
                            lazy='subquery', back_populates='genres')

    def __str__(self):
        return self.name


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True,
                         nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    image_file = db.Column(db.String(20), nullable=False,
                           default='default.jpg')
    loans = db.relationship('Loan', back_populates='user', lazy=True)
    is_admin = db.Column(db.Boolean, default=False)
    favorites = db.relationship('Book', secondary=favorites, lazy='subquery',
                                backref=db.backref('favorited_by', lazy=True))
    # Add relation to notifications
    received_notifications = db.relationship(
        'Notification', foreign_keys='Notification.recipient_id', back_populates='recipient', lazy=True, cascade='all, delete-orphan')
    sent_notifications = db.relationship(
        'Notification', foreign_keys='Notification.sender_id', back_populates='sender', lazy=True)

    comments = db.relationship('Comment', back_populates='user', lazy=True, cascade='all, delete-orphan')

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
    reservation_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    issue_date = db.Column(db.DateTime)
    return_date = db.Column(db.DateTime)

    status = db.Column(db.String(50), default='pending', nullable=False)

    book = db.relationship('Book', backref='loans')
    user = db.relationship('User', back_populates='loans')

    # Add relation to the notifications
    notifications = db.relationship(
        'Notification', back_populates='loan', lazy=True, cascade='all, delete-orphan')

    def __str__(self):
        return f"Loan {self.id}: {self.book.title} to {self.user.username} - Status: {self.status}"


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    message = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    type = db.Column(db.String(100), nullable=False)
    loan_id = db.Column(db.Integer, db.ForeignKey('loan.id'), nullable=True)

    recipient = db.relationship(
        'User', foreign_keys=[recipient_id], back_populates='received_notifications')
    sender = db.relationship('User', foreign_keys=[
                             sender_id], back_populates='sent_notifications')
    loan = db.relationship('Loan', back_populates='notifications')

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.message[:50]}..."

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)

    user = db.relationship('User', back_populates='comments')
    book = db.relationship('Book', back_populates='comments')

    def __str__(self):
        return f"Comment by {self.user.username} on {self.book.title} at {self.timestamp}"