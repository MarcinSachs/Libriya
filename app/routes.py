import os
from datetime import datetime
import secrets
import re
import requests
from urllib.parse import urlparse
from functools import wraps
from flask_session import Session
from sqlalchemy import or_
from werkzeug.datastructures import FileStorage
from flask import (
    jsonify,
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
    make_response,
    session,
)
from werkzeug.utils import secure_filename

from app import db
from app.forms import BookForm, LoanForm, UserEditForm, UserForm, UserSettingsForm
from app.models import Author, Book, Genre, Loan, User, Notification, db
from flask_login import login_user, login_required, current_user, logout_user

from flask_babel import _, ngettext

bp = Blueprint("main", __name__)


# Decorator to check if user is admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash(
                _("You do not have administrative privileges to access this page."), "danger")
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

# Function to check notifications


def create_notification(recipients, sender, message, notification_type, loan=None):
    if not isinstance(recipients, list):
        recipients = [recipients]

    for recipient in recipients:
        new_notification = Notification(
            recipient=recipient,
            sender=sender,
            message=message,
            type=notification_type,
            loan=loan
        )
        db.session.add(new_notification)
    db.session.commit()


@bp.route("/favicon.ico")
def favicon():
    return current_app.send_static_file("favicon.ico")

# Home Page


@bp.route("/")
@login_required
def home():
    status_filter = request.args.get('status')
    genre_filter = request.args.get('genre')
    title_filter = request.args.get('title')

    query = Book.query

    if title_filter: 
        query = query.filter(Book.title.ilike(f"%{title_filter}%"))

    if status_filter:
        if status_filter == 'available':
            query = query.filter(Book.status == 'available')
        elif status_filter == 'on_loan':
            query = query.filter(
                or_(Book.status == 'on_loan', Book.status == 'reserved'))

    if genre_filter:
        query = query.filter(Book.genre_id == genre_filter)

    books = query.all()
    genres = Genre.query.all()
    genres = sorted(genres, key=lambda g: _(g.name))
    
    # Numbers of unread notifications to layout
    unread_notifications_count = Notification.query.filter_by(
        recipient=current_user, is_read=False
    ).count()

    return render_template("index.html", books=books, genres=genres, active_page="books",
                           unread_notifications_count=unread_notifications_count)

# Login and Logout


@bp.route("/login/")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    return render_template("login.html", login_page=True, title='Log In')


@bp.route("/login/", methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user)
        flash(_('Login successful!'), 'success')
        return redirect(url_for('main.home'))
    else:
        flash(_('Invalid username or password. Please try again.'), 'danger')
        return redirect(url_for('main.login'))


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash(_('You have been logged out.'), 'info')
    return redirect(url_for('main.login'))

# Users


@bp.route("/users/")
@login_required
@admin_required
def users():
    all_users = db.session.query(User).distinct().all()
    return render_template("users.html", users=all_users, active_page="users", parent_page="admin")


@bp.route("/users/add/", methods=["GET", "POST"])
@login_required
@admin_required
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
        flash(f"User '{user.username}' added successfully!", "success")
        return redirect(url_for("main.users"))
    return render_template("user_add.html", form=form, parent_page="admin", active_page="users")


@bp.route("/users/edit/<int:user_id>", methods=["GET", "POST"])
@login_required
def user_edit(user_id):
    user = User.query.get_or_404(user_id)
    form = UserEditForm(obj=user)

    if form.validate_on_submit():
        # user.username is readonly, so no need to update

        # Prevent the last admin from revoking their own privileges
        if user.is_admin and not form.is_admin.data and User.query.filter_by(is_admin=True).count() == 1:
            flash("You cannot revoke the last administrator's privileges.", "danger")
            return redirect(url_for('main.user_edit', user_id=user.id))

        user.email = form.email.data
        user.is_admin = form.is_admin.data
        db.session.commit()
        flash(_("User '%(username)s' updated successfully!",
              username=user.username), "success")
        return redirect(url_for("main.users"))

    return render_template(
        "user_edit.html",
        form=form,
        user=user,
        parent_page="admin",
        active_page="users",
        title=f"Edit User: {user.username}"
    )


@bp.route("/user/profile/<int:user_id>")
@login_required
def user_profile(user_id):
    user = current_user
    # Sort all loans by date, newest first
    all_loans = sorted(
        user.loans, key=lambda x: x.reservation_date, reverse=True)
    active_loans = [loan for loan in all_loans if loan.status == 'active']
    loan_history = [loan for loan in all_loans if loan.status ==
                    'returned' or loan.status == 'cancelled']
    pending_loans = [loan for loan in all_loans if loan.status == 'pending']

    # Access favorites
    favorite_books = user.favorites

    return render_template(
        "user_profile.html",
        user=user,
        loans=all_loans,
        active_loans=active_loans,
        loan_history=loan_history,
        pending_loans=pending_loans,
        favorite_books=favorite_books,
        title=f"{user.username}"
    )


@bp.route("/user/settings", methods=["GET", "POST"])
@login_required
def user_settings():
    user = current_user
    if not user:
        flash(_("No user found to edit settings."), "danger")
        return redirect(url_for('main.home'))

    form = UserSettingsForm(obj=user)

    if form.validate_on_submit():
        if form.picture.data:
            # Create a secure, unique filename
            random_hex = secrets.token_hex(8)
            _, f_ext = os.path.splitext(form.picture.data.filename)
            picture_filename = random_hex + f_ext
            picture_path = os.path.join(
                current_app.config["UPLOAD_FOLDER"], picture_filename)
            form.picture.data.save(picture_path)
            user.image_file = picture_filename

        user.email = form.email.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash(_("Your settings have been updated."), "success")
        return redirect(url_for('main.user_profile', user_id=user.id))

    image_file_url = url_for('static', filename='uploads/' + user.image_file)
    return render_template("user_settings.html", form=form, title="My Settings", image_file_url=image_file_url, user=user)

# Books


@bp.route("/book/<int:book_id>")
@login_required
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    return render_template("book_detail.html", book=book, active_page="books")


@bp.route("/books/add/", methods=["GET", "POST"])
@login_required
@admin_required
def book_add():
    form = BookForm()

    if form.validate_on_submit():

        # Handle genre
        genre_id = form.genre.data  # Get genre ID from form
        genre = Genre.query.get(genre_id)

        if not genre:
            flash(_('Invalid genre.'), 'danger')
            return render_template('book_add.html', form=form)

        new_book = Book(
            isbn=form.isbn.data,
            title=form.title.data,
            genre=genre,
            year=form.year.data,
            status='available'
        )

        # Handle multiple authors
        author_names = [name.strip()
                        for name in form.author.data.split(',') if name.strip()]
        for name in author_names:
            author = Author.query.filter_by(name=name).first()
            if not author:
                author = Author(name=name)
                db.session.add(author)
            new_book.authors.append(author)

        if form.cover.data:
            f = form.cover.data
            cover_filename = secure_filename(f.filename)
            # UPLOAD_FOLDER must be defined in your config.py
            f.save(os.path.join(
                current_app.config["UPLOAD_FOLDER"], cover_filename))
            new_book.cover = cover_filename
        elif 'cover_url' in request.form and request.form['cover_url']:
            cover_url = request.form['cover_url']
            try:
                response = requests.get(cover_url, stream=True, timeout=10)
                if response.status_code == 200:
                    # Create a secure, unique filename from the URL
                    random_hex = secrets.token_hex(8)
                    # Get file extension from URL path
                    _, f_ext = os.path.splitext(urlparse(cover_url).path)
                    if not f_ext:
                        f_ext = '.jpg'  # Default extension
                    cover_filename = random_hex + f_ext
                    picture_path = os.path.join(
                        current_app.config["UPLOAD_FOLDER"], cover_filename)
                    with open(picture_path, 'wb') as f:
                        f.write(response.content)
                    new_book.cover = cover_filename
            except requests.exceptions.RequestException as e:
                flash(_("Could not download cover image: '%(e)s'", e=e), "danger")

        db.session.add(new_book)
        db.session.commit()
        flash(_("Book added successfully!"), "success")
        # Redirect to the home page, which is part of the 'main' blueprint
        return redirect(url_for("main.home"))

    return render_template("book_add.html", form=form)


@bp.route("/book_delete/<int:book_id>", methods=["POST"])
@login_required
@admin_required
def book_delete(book_id):
    book = Book.query.get_or_404(book_id)

    # Prevent deletion if the book has any associated loans (active or past)
    if book.status != 'available':
        flash(_('Cannot delete "%(title)s" because it is currently "%(status)s". Consider marking it as inactive instead.',
              title=book.title, status=book.status), "danger")
        return redirect(url_for("main.home"))

    db.session.delete(book)
    db.session.commit()
    flash(_("Book deleted successfully!"), "success")
    return redirect(url_for("main.home"))


@bp.route("/book_edit/<int:book_id>", methods=["GET", "POST"])
@login_required
@admin_required
def book_edit(book_id):
    book = Book.query.get_or_404(book_id)
    author_string = ", ".join([author.name for author in book.authors])
    # Populate form with existing data, including related fields
    form = BookForm(obj=book, author=author_string, genre=book.genre.name)
    genres = [g.name for g in Genre.query.distinct(Genre.name).all()]

    if form.validate_on_submit():
        # Update book fields from form data
        book.isbn = form.isbn.data
        book.title = form.title.data
        book.year = form.year.data

        # Handle multiple authors
        book.authors.clear()
        author_names = [name.strip()
                        for name in form.author.data.split(',') if name.strip()]
        for name in author_names:
            author = Author.query.filter_by(name=name).first()
            if not author:
                author = Author(name=name)
                db.session.add(author)
            book.authors.append(author)

        genre_id = form.genre.data
        genre = Genre.query.get(genre_id)
        if not genre:
            return render_template('book_edit.html', form=form, book=book, genres=genres, active_page="books", title="Edit Book")
        book.genre = genre

        # Handle cover update
        if form.cover.data:
            if isinstance(form.cover.data, FileStorage):
                f = form.cover.data
                cover_filename = secure_filename(f.filename)
                f.save(os.path.join(
                    current_app.config["UPLOAD_FOLDER"], cover_filename))
                book.cover = cover_filename

        db.session.commit()
        flash(_("Book updated successfully!"), "success")
        return redirect(url_for("main.home"))
    return render_template("book_edit.html", form=form, book=book, genres=genres, active_page="books", title="Edit Book")

# Favorites


@bp.route('/favorites/add/<int:book_id>', methods=['POST'])
@login_required
def add_favorite(book_id):
    user = current_user
    book = Book.query.get_or_404(book_id)
    if book in user.favorites:
        flash(_('Book is already in favorites.'), 'info')
    else:
        user.favorites.append(book)
        db.session.commit()
        flash(_('Book added to favorites.'), 'success')
    return redirect(url_for('main.home'))
    # return redirect(url_for('main.book_detail', book_id=book.id))


@bp.route('/favorites/remove/<int:book_id>', methods=['POST'])
@login_required
def remove_favorite(book_id):
    user = current_user
    book = Book.query.get_or_404(book_id)
    if book in user.favorites:
        user.favorites.remove(book)
        db.session.commit()
        flash(_('Book removed from favorites.'), 'success')
    else:
        flash(_('Book is not in favorites.'), 'info')
    return redirect(url_for('main.book_detail', book_id=book.id))

# Loans


@bp.route("/loans/")
@login_required
@admin_required
def loans():
    loan_query = Loan.query.join(Book).join(User)
    # Apply user filter
    user_filter_id = request.args.get('user')
    if user_filter_id:
        try:
            user_filter_id = int(user_filter_id)
            loan_query = loan_query.filter(Loan.user_id == user_filter_id)
        except ValueError:
            # Handle case where user_filter_id is not a valid integer
            # You might want to flash an error message here, or just ignore the filter
            flash(_("Invalid user ID provided for filtering."), "danger")
     # Apply status filter
    status_filter = request.args.get('status')
    if status_filter:
        loan_query = loan_query.filter(Loan.status == status_filter)

    # Order the results for consistent display (e.g., by loan date descending)
    loan_query = loan_query.order_by(Loan.reservation_date.desc())

    # Execute the final query to get filtered loans
    filtered_loans = loan_query.all()

    # Get all users for the user filter dropdown (always need all for the selection)
    all_users = User.query.order_by(User.username).all()

    unread_notifications_count = Notification.query.filter_by(
        recipient=current_user, is_read=False
    ).count()

    return render_template("loans.html", loans=filtered_loans, users=all_users, active_page="loans", parent_page="admin", title=_("Loans"),
                           now=datetime.utcnow())


@bp.route("/request_reservation/<int:book_id>/<int:user_id>", methods=["GET", "POST"])
@login_required
def request_reservation(book_id, user_id):
    book = Book.query.get_or_404(book_id)
    user = User.query.get_or_404(user_id)

    # Check if book is avaible
    if book.status == 'available':
        # Check if user do not have reservation
        existing_loan = Loan.query.filter_by(
            book_id=book.id, user_id=user.id
        ).filter(or_(Loan.status == 'pending', Loan.status == 'active')).first()

        if existing_loan:
            flash(
                _("You already have an active or pending reservation for this book."), "info")
            return redirect(url_for("main.home"))

        # Change status to 'reserved'
        book.status = 'reserved'
        # Create new record with pending status
        new_loan = Loan(book=book, user=user,
                        reservation_date=datetime.utcnow(), status='pending')
        db.session.add(new_loan)
        db.session.commit()

        # --- Notifications for admins ---
        admins = User.query.filter_by(is_admin=True).all()
        message = _("%(username)s has requested to reserve \"%(title)s\".",
                    username=user.username, title=book.title)
        create_notification(admins, current_user, message,
                            'reservation_request', loan=new_loan)

        flash(_("Book has been reserved successfully! An admin will approve it shortly."), "success")
    elif book.status == 'reserved':
        flash(_("This book is already reserved by another user."), "danger")
    elif book.status == 'on_loan':
        flash(_("This book is currently on loan."), "danger")
    return redirect(url_for("main.home"))


@bp.route("/borrow/<int:book_id>/<int:user_id>", methods=["GET", "POST"])
@login_required
def borrow_book(book_id, user_id):
    book = Book.query.get_or_404(book_id)
    user = User.query.get_or_404(user_id)
    if book.is_available:
        book.is_available = False
        new_loan = Loan(book=book, user=user)
        db.session.add(new_loan)
        db.session.commit()
        flash(_("Book borrowed successfully!"), "success")
    else:
        flash(_("This book is already on loan."), "danger")
    return redirect(url_for("main.home"))


@bp.route("/return_book/<int:book_id>", methods=["GET", "POST"])
@login_required
def return_book(book_id):
    loan = Loan.query.filter_by(book_id=book_id, return_date=None).first()
    if loan:
        loan.book.is_available = True
        loan.return_date = datetime.utcnow()
        db.session.commit()
        flash(_("Book returned successfully!"), "success")
    else:
        flash(_("This book is not currently on loan."), "danger")
    return redirect(url_for("main.home"))


@bp.route('/loans/approve/<int:loan_id>', methods=['POST'])
@login_required
@admin_required
def approve_loan(loan_id):
    loan = Loan.query.get_or_404(loan_id)

    if loan.status == 'pending':
        # Check if book is already in reserved status and was not cancelled
        if loan.book.status == 'reserved':
            loan.status = 'active'
            loan.issue_date = datetime.utcnow()
            loan.book.status = 'on_loan'
            db.session.commit()

            # --- Create notification for users ---
            message = _(
                "Your reservation for \"%(title)s\" has been approved!", title=loan.book.title)
            create_notification(loan.user, current_user,
                                message, 'loan_approved', loan=loan)

            flash(_('Loan for "%(title)s" to %(username)s has been approved!',
                    title=loan.book.title, username=loan.user.username), 'success')
        else:
            flash(_('Cannot approve loan: Book status is not "reserved". It might have been cancelled or loaned differently.'), 'danger')
    else:
        flash(_('Loan is not in "pending" status and cannot be approved.'), 'info')
    return redirect(url_for('main.loans'))


@bp.route('/loans/cancel/<int:loan_id>', methods=['POST'])
@login_required
@admin_required
def cancel_loan(loan_id):
    loan = Loan.query.get_or_404(loan_id)

    if loan.status == 'pending':
        # Return 'available' status if was reserved
        if loan.book.status == 'reserved':
            loan.book.status = 'available'
        loan.status = 'cancelled'
        db.session.commit()

        # --- Create notification for users ---
        message = _("Your reservation for \"%(title)s\" has been cancelled by an administrator.",
                    title=loan.book.title)
        create_notification(loan.user, current_user,
                            message, 'loan_cancelled', loan=loan)

        flash(_('Reservation for "%(title)s" by %(username)s has been cancelled.',
                title=loan.book.title, username=loan.user.username), 'info')
    else:
        flash(_('Cannot cancel loan: It is not in "pending" status.'), 'danger')
    return redirect(url_for('main.loans'))


@bp.route('/loans/return/<int:loan_id>', methods=['POST'])
@login_required
@admin_required
def return_loan(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    if loan.status == 'active':
        loan.book.status = 'available'
        loan.return_date = datetime.utcnow()
        loan.status = 'returned'
        db.session.commit()

        # --- Create notification for user ---
        message = _("The book \"%(title)s\" that you loaned has been marked as returned.",
                    title=loan.book.title)
        create_notification(loan.user, current_user,
                            message, 'loan_returned', loan=loan)

        flash(_('Book "%(title)s" has been returned.',
              title=loan.book.title), 'success')
    else:
        flash(_('This loan is not active or has already been returned.'), 'info')
    return redirect(url_for('main.loans'))


@bp.route("/loans/<user_id>")
@login_required
def user_loans(user_id):
    user_loans = User.query.get_or_404(user_id).loans
    user_loans = sorted(
        user_loans, key=lambda x: x.reservation_date, reverse=True)
    return render_template("loans.html", loans=user_loans, active_page="", title="My Loans")


@bp.route("/loans/add/", methods=["GET", "POST"])
@login_required
@admin_required
def loan_add():
    form = LoanForm()
    # Populate choices for books and users
    # We only want to loan available books
    form.book_id.choices = [(b.id, b.title) for b in Book.query.filter_by(
        status='available').order_by(Book.title).all()]
    form.user_id.choices = [(u.id, u.username)
                            for u in User.query.order_by(User.username).all()]

    if form.validate_on_submit():
        book = Book.query.get(form.book_id.data)
        user = User.query.get(form.user_id.data)
        if book and user and book.status == 'available':
            book.status = 'on_loan'
            new_loan = Loan(book=book, user=user,
                            reservation_date=datetime.utcnow(),
                            issue_date=datetime.utcnow(),
                            status='active')
            db.session.add(new_loan)
            db.session.commit()

            # --- Create notification for user ---
            message = _("A loan for \"%(title)s\" has been directly issued to you by an administrator.",
                        title=book.title)
            create_notification(user, current_user, message,
                                'admin_issued_loan', loan=new_loan)

            flash(_("Loan added successfully!"), "success")
            return redirect(url_for("main.loans"))
        elif book and (book.status == 'on_loan' or book.status == 'reserved'):
            flash(_("This book is currently on loan or reserved."), "danger")
        else:
            flash(_("Invalid book or user."), "danger")
    return render_template("loan_add.html", form=form, active_page="loans", parent_page="admin", title="Add Loan")


@bp.route('/user/loans/cancel/<int:loan_id>', methods=['POST'])
@login_required
def user_cancel_reservation(loan_id):
    loan = Loan.query.get_or_404(loan_id)

    # Sprawdź, czy to wypożyczenie należy do aktualnie zalogowanego użytkownika
    if loan.user_id != current_user.id:
        flash(_("You can only cancel your own reservations."), "danger")
        return redirect(url_for('main.user_profile', user_id=current_user.id))

    # Sprawdź, czy wypożyczenie ma status "oczekujące"
    if loan.status == 'pending':
        # Przywróć status książki na 'available' tylko jeśli była zarezerwowana przez to konkretne wypożyczenie
        if loan.book.status == 'reserved':
            loan.book.status = 'available'
        loan.status = 'cancelled'  # Zmień status wypożyczenia na "anulowane"
        db.session.commit()

        # --- Create notyfication for admin ---
        admins = User.query.filter_by(is_admin=True).all()
        message = _("%(username)s has cancelled their reservation for \"%(title)s\".",
                    username=current_user.username, title=loan.book.title)
        create_notification(admins, current_user, message,
                            'user_cancelled_reservation', loan=loan)

        flash(_("Your reservation for '%(title)s' has been cancelled.",
              title=loan.book.title), 'success')
    else:
        # Jeśli status nie jest "pending", nie można anulować przez użytkownika
        flash(_("This reservation cannot be cancelled as it is not in 'pending' status."), 'danger')

    return redirect(url_for('main.user_profile', user_id=current_user.id))
# Language selection


@bp.route('/set_language/<lang>')
def set_language(lang):
    if lang in current_app.config['LANGUAGES']:
        # Create a response object from the redirect to set a cookie
        response = make_response(
            redirect(request.referrer or url_for('main.home')))
        # Set cookie for 2 years
        response.set_cookie('language', lang, max_age=60*60*24*365*2)
        flash(_('Language changed to %(lang)s.', lang=lang), 'info')
        return response
    flash(_('Unsupported language.'), 'danger')
    return redirect(request.referrer or url_for('main.home'))

# Notifications


@bp.route("/notifications/")
@login_required
def view_notifications():
    if current_user.is_admin:
        notifications = Notification.query.filter(
            Notification.recipient_id == current_user.id).order_by(Notification.timestamp.desc()).all()
    else:
        notifications = Notification.query.filter_by(
            recipient=current_user).order_by(Notification.timestamp.desc()).all()

    unread_notifications_count = Notification.query.filter_by(
        recipient=current_user, is_read=False
    ).count()

    return render_template("notifications.html", notifications=notifications, title=_("Your Notifications"),
                           unread_notifications_count=unread_notifications_count)


@bp.route("/notifications/mark_read/<int:notification_id>", methods=['POST'])
@login_required
def mark_notification_as_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)

    if notification.recipient_id != current_user.id and not current_user.is_admin:
        flash(_("You do not have permission to mark this notification as read."), "danger")
        return redirect(url_for('main.view_notifications'))

    notification.is_read = True
    db.session.commit()
    flash(_("Notification marked as read."), "success")
    return redirect(url_for('main.view_notifications'))


@bp.route("/notifications/mark_all_read/", methods=['POST'])
@login_required
def mark_all_notifications_as_read():
    notifications_to_mark = Notification.query.filter_by(
        recipient=current_user, is_read=False
    ).all()

    for notification in notifications_to_mark:
        notification.is_read = True
    db.session.commit()
    flash(_("All notifications marked as read."), "success")
    return redirect(url_for('main.view_notifications'))


@bp.route("/admin/send_overdue_reminder/<int:loan_id>", methods=['POST'])
@login_required
@admin_required
def send_overdue_reminder(loan_id):
    loan = Loan.query.get_or_404(loan_id)

    if loan.status == 'active' and loan.issue_date and (datetime.utcnow() - loan.issue_date).days > 14:
        message = _("Reminder: Your loan for \"%(title)s\" is overdue. Please return it as soon as possible.",
                    title=loan.book.title)
        create_notification(loan.user, current_user, message,
                            'overdue_reminder', loan=loan)
        flash(_("Overdue reminder sent to %(username)s for book \"%(title)s\".",
                username=loan.user.username, title=loan.book.title), "success")
    else:
        flash(
            _("Cannot send overdue reminder. Loan is not active or not overdue."), "danger")

    return redirect(url_for('main.loans'))

# API for ISBN lookup


@bp.route("/api/v1/isbn/<isbn>", methods=["GET"])
@login_required
def get_book_by_isbn(isbn):
    """
    API endpoint to fetch book data from OpenLibrary based on ISBN.
    """
    url = "https://openlibrary.org/api/books"
    params = {
        "bibkeys": f"ISBN:{isbn}",
        "jscmd": "data",
        "format": "json"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        data = response.json()
        book_data = data.get(f"ISBN:{isbn}")

        if not book_data:
            return jsonify({"error": "No data found for this ISBN."}), 404

        # Extract relevant fields
        book_info = {
            "title": book_data.get("title"),
            "author": ", ".join(author["name"] for author in book_data.get("authors", [])),
            "cover_image": book_data.get("cover", {}).get("large"),
        }

        publish_date_str = book_data.get("publish_date", "")
        if publish_date_str:
            match = re.search(r'\d{4}', publish_date_str)
            if match:
                book_info["year"] = match.group(0)

        return jsonify(book_info)
    except requests.exceptions.RequestException as e:
        # Handle network errors, timeouts, etc.
        return jsonify({"error": f"Network error connecting to Open Library: {e}"}), 500
    except Exception as e:
        # Handle other potential errors (e.g., JSON decoding)
        return jsonify({"error": str(e)}), 500

# Global context for notification count


@bp.context_processor
def inject_unread_notifications_count():
    if current_user.is_authenticated:
        unread_count = Notification.query.filter_by(
            recipient=current_user, is_read=False).count()
        return {'unread_notifications_count': unread_count}
    return {'unread_notifications_count': 0}
