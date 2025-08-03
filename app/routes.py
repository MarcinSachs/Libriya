import os
from datetime import datetime
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
from app.forms import BookForm, UserForm, LoanForm
from app.models import Author, Book, Genre, Loan, User

bp = Blueprint("main", __name__)

# Set the active user for the session


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


@bp.route("/book_delete/<int:book_id>", methods=["POST"])
def book_delete(book_id):
    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    flash("Book deleted successfully!", "success")
    return redirect(url_for("main.home"))


@bp.route("/book_edit/<int:book_id>", methods=["GET", "POST"])
def book_edit(book_id):
    book = Book.query.get_or_404(book_id)
    # Populate form with existing data, including related fields
    form = BookForm(obj=book, author=book.author.name, genre=book.genre.name)
    genres = [g.name for g in Genre.query.distinct(Genre.name).all()]

    if form.validate_on_submit():
        # Update book fields from form data
        book.isbn = form.isbn.data
        book.title = form.title.data
        book.year = form.year.data

        # Find or create author and genre
        author = Author.query.filter_by(name=form.author.data).first()
        if not author:
            author = Author(name=form.author.data)
        book.author = author

        genre = Genre.query.filter_by(name=form.genre.data).first()
        if not genre:
            genre = Genre(name=form.genre.data)
        book.genre = genre

        # Handle cover update
        if form.cover.data:
            f = form.cover.data
            cover_filename = secure_filename(f.filename)
            f.save(os.path.join(
                current_app.config["UPLOAD_FOLDER"], cover_filename))
            book.cover = cover_filename

        db.session.commit()
        flash("Book updated successfully!", "success")
        return redirect(url_for("main.home"))
    return render_template("book_edit.html", form=form, book=book, genres=genres, active_page="books", title="Edit Book")


@bp.route("/loans/")
def loans():
    all_loans = Loan.query.all()
    return render_template("loans.html", loans=all_loans, active_page="loans", title="Loans")


@bp.route("/borrow/<int:book_id>/<int:user_id>", methods=["GET", "POST"])
def borrow_book(book_id, user_id):
    book = Book.query.get_or_404(book_id)
    user = User.query.get_or_404(user_id)
    if book.is_available:
        book.is_available = False
        new_loan = Loan(book=book, user=user)
        db.session.add(new_loan)
        db.session.commit()
        flash("Book borrowed successfully!", "success")
    else:
        flash("This book is already on loan.", "danger")
    return redirect(url_for("main.home"))


@bp.route("/return_book/<int:book_id>", methods=["GET", "POST"])
def return_book(book_id):
    loan = Loan.query.filter_by(book_id=book_id, return_date=None).first()
    if loan:
        loan.book.is_available = True
        loan.return_date = datetime.utcnow()
        db.session.commit()
        flash("Book returned successfully!", "success")
    else:
        flash("This book is not currently on loan.", "danger")
    return redirect(url_for("main.home"))


@bp.route("/loans/add/", methods=["GET", "POST"])
def loan_add():
    form = LoanForm()
    # Populate choices for books and users
    # We only want to loan available books
    form.book_id.choices = [(b.id, b.title) for b in Book.query.filter_by(
        is_available=True).order_by(Book.title).all()]
    form.user_id.choices = [(u.id, u.username)
                            for u in User.query.order_by(User.username).all()]

    if form.validate_on_submit():
        book = Book.query.get(form.book_id.data)
        user = User.query.get(form.user_id.data)
        if book and user and book.is_available:
            # Mark book as unavailable
            book.is_available = False
            new_loan = Loan(book=book, user=user)
            db.session.add(new_loan)
            db.session.commit()
            flash("Loan added successfully!", "success")
            return redirect(url_for("main.loans"))
        elif book and not book.is_available:
            flash("This book is already on loan.", "danger")
        else:
            flash("Invalid book or user.", "danger")
    return render_template("loan_add.html", form=form, active_page="loans", title="Add Loan")


@bp.route('/loans/return/<int:loan_id>', methods=['POST'])
def return_loan(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    if loan.return_date is None:
        loan.return_date = datetime.utcnow()
        loan.book.is_available = True
        db.session.commit()
        flash(f'Book "{loan.book.title}" has been returned.', 'success')
    else:
        flash('This book has already been returned.', 'info')
    return redirect(url_for('main.loans'))
