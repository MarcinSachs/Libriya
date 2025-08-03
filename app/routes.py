import os
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    url_for,
)
from werkzeug.utils import secure_filename

from app import db
from app.forms import BookForm, UserForm
from app.models import Author, Book, Genre, User

bp = Blueprint("main", __name__)


@bp.route("/favicon.ico")
def favicon():
    return current_app.send_static_file("favicon.ico")


@bp.route("/")
def home():
    all_books = Book.query.all()
    return render_template("index.html", books=all_books, active_page="books")


@bp.route("/users/")
def users():
    all_users = db.session.query(User).distinct().all()
    return render_template("users.html", users=all_users, active_page="users")


@bp.route("/users/add/", methods=["GET", "POST"])
def user_add():
    form = UserForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        # Create a new user and set their password
        user = User(username=username, email=email)
        user.set_password(password)
        # Add the user to the database
        db.session.add(user)
        db.session.commit()
        flash("User added successfully!", "success")
        return redirect(url_for("main.users"))
    return render_template("user_add.html", form=form)


@bp.route("/books/add/", methods=["GET", "POST"])
def book_add():
    form = BookForm()
    # This provides a list of existing genres for autocompletion in the form
    genres = [g.name for g in Genre.query.distinct(Genre.name).all()]

    if form.validate_on_submit():
        # Find or create author and genre
        author = Author.query.filter_by(name=form.author.data).first()
        if not author:
            author = Author(name=form.author.data)

        genre = Genre.query.filter_by(name=form.genre.data).first()
        if not genre:
            genre = Genre(name=form.genre.data)

        new_book = Book(
            isbn=form.isbn.data,
            title=form.title.data,
            author=author,
            genre=genre,
            year=form.year.data,
        )

        if form.cover.data:
            f = form.cover.data
            cover_filename = secure_filename(f.filename)
            # UPLOAD_FOLDER must be defined in your config.py
            f.save(os.path.join(
                current_app.config["UPLOAD_FOLDER"], cover_filename))
            new_book.cover = cover_filename

        db.session.add(new_book)
        db.session.commit()
        flash("Book added successfully!", "success")
        # Redirect to the home page, which is part of the 'main' blueprint
        return redirect(url_for("main.home"))

    return render_template("book_add.html", form=form, genres=genres)
