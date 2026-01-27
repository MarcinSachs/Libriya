import os
import secrets
import requests
from urllib.parse import urlparse
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from flask_babel import _
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from app import db
from app.forms import BookForm
from app.models import Book, Author, Library, Location
from app.utils import role_required
from app.utils.audit_log import log_book_deleted

bp = Blueprint("books", __name__)


@bp.route("/book/<int:book_id>", methods=['GET', 'POST'])
@login_required
def book_detail(book_id):
    from app.forms import CommentForm
    from app.models import Comment

    book = Book.query.get_or_404(book_id)
    user_comment = Comment.query.filter_by(
        book_id=book.id,
        user_id=current_user.id
    ).first()

    comment_form = CommentForm(obj=user_comment)

    if comment_form.validate_on_submit() and request.method == 'POST':
        if user_comment:
            user_comment.text = comment_form.text.data
            user_comment.timestamp = datetime.utcnow()
            db.session.commit()
            flash(_('Your comment has been updated!'), 'success')
        else:
            new_comment = Comment(
                text=comment_form.text.data,
                book=book,
                user=current_user
            )
            db.session.add(new_comment)
            db.session.commit()
            flash(_('Your comment has been added!'), 'success')

        return redirect(url_for('books.book_detail', book_id=book.id))

    return render_template("book_detail.html", book=book, active_page="books",
                           user_comment=user_comment, comment_form=comment_form)


@bp.route("/books/add/", methods=["GET", "POST"])
@login_required
@role_required('admin', 'manager')
def book_add():
    form = BookForm()

    # --- Populate Library Choices ---
    if current_user.role == 'admin':
        form.library.choices = [
            (lib.id, lib.name)
            for lib in Library.query.order_by('name').all()
        ]
    else:  # manager
        form.library.choices = [
            (lib.id, lib.name) for lib in current_user.libraries
        ]
        # If manager has only one library, set it as default
        if len(current_user.libraries) == 1:
            form.library.data = current_user.libraries[0].id

    if form.validate_on_submit():
        new_book = Book(
            isbn=form.isbn.data,
            title=form.title.data,
            year=form.year.data,
            library_id=form.library.data,  # Assign library
            status='available'
        )

        author_names = [name.strip()
                        for name in form.author.data.split(',') if name.strip()]
        for name in author_names:
            author = Author.query.filter_by(name=name).first()
            if not author:
                author = Author(name=name)
                db.session.add(author)
            new_book.authors.append(author)

        selected_genres = form.genres.data
        new_book.genres.extend(selected_genres)

        if form.cover.data:
            f = form.cover.data
            cover_filename = secure_filename(f.filename)
            f.save(os.path.join(
                current_app.config["UPLOAD_FOLDER"], cover_filename))
            new_book.cover = cover_filename
        elif 'cover_url' in request.form and request.form['cover_url']:
            cover_url = request.form['cover_url']
            try:
                # SECURITY: Validate URL to prevent SSRF attacks
                parsed_url = urlparse(cover_url)

                # Only allow http and https protocols
                if parsed_url.scheme not in ['http', 'https']:
                    raise ValueError("Invalid URL scheme. Only HTTP(S) allowed.")

                # Prevent localhost and private IPs
                blocked_hosts = ['localhost', '127.0.0.1', '0.0.0.0']
                if parsed_url.netloc in blocked_hosts:
                    raise ValueError("Cannot access local network addresses.")

                # Check for private IP ranges
                import ipaddress
                try:
                    ip = ipaddress.ip_address(parsed_url.hostname)
                    if ip.is_private or ip.is_loopback:
                        raise ValueError("Cannot access private IP addresses.")
                except (ValueError, TypeError):
                    # If hostname is not an IP, it's likely a domain name (OK)
                    pass

                # Fetch the image with timeout and size limits
                response = requests.get(cover_url, stream=True, timeout=10)
                response.raise_for_status()

                if response.status_code == 200:
                    # Check content-length before downloading
                    content_length = response.headers.get('content-length')
                    max_size = 5 * 1024 * 1024  # 5MB limit
                    if content_length and int(content_length) > max_size:
                        raise ValueError("File too large. Maximum 5MB allowed.")

                    # Check actual downloaded size
                    downloaded_size = 0
                    content = b''
                    for chunk in response.iter_content(chunk_size=1024):
                        downloaded_size += len(chunk)
                        if downloaded_size > max_size:
                            raise ValueError("File too large. Maximum 5MB allowed.")
                        content += chunk

                    # Validate file extension
                    random_hex = secrets.token_hex(8)
                    _, f_ext = os.path.splitext(urlparse(cover_url).path)
                    if not f_ext or f_ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif']:
                        f_ext = '.jpg'
                    cover_filename = random_hex + f_ext
                    picture_path = os.path.join(
                        current_app.config["UPLOAD_FOLDER"], cover_filename)
                    with open(picture_path, 'wb') as f:
                        f.write(content)
                    new_book.cover = cover_filename
            except (requests.exceptions.RequestException, ValueError) as e:
                flash(
                    _("Could not download cover image: %(error)s", error=str(e)), "danger")

        db.session.add(new_book)
        db.session.commit()

        # Add location if any location field is provided
        if any([form.shelf.data, form.section.data, form.room.data, form.location_notes.data]):
            location = Location(
                book_id=new_book.id,
                shelf=form.shelf.data or None,
                section=form.section.data or None,
                room=form.room.data or None,
                notes=form.location_notes.data or None
            )
            db.session.add(location)
            db.session.commit()

        flash(_("Book added successfully!"), "success")
        return redirect(url_for("main.home"))

    return render_template("book_add.html", form=form)


@bp.route("/book_delete/<int:book_id>", methods=["POST"])
@login_required
@role_required('admin')
def book_delete(book_id):
    book = Book.query.get_or_404(book_id)

    # Prevent deletion if the book has any associated loans (active or past)
    if book.status != 'available':
        flash(_('Cannot delete "%(title)s" because it is currently '
                '"%(status)s". Consider marking it as inactive instead.',
              title=book.title, status=book.status), "danger")
        return redirect(url_for("main.home"))

    # Log book deletion before removing it
    log_book_deleted(book.id, book.title)

    db.session.delete(book)
    db.session.commit()
    flash(_("Book deleted successfully!"), "success")
    return redirect(url_for("main.home"))


@bp.route("/book_edit/<int:book_id>", methods=["GET", "POST"])
@login_required
@role_required('admin', 'manager')
def book_edit(book_id):
    book = Book.query.get_or_404(book_id)

    # --- Authorization ---
    if current_user.role == 'manager':
        user_libs_ids = [lib.id for lib in current_user.libraries]
        if book.library_id not in user_libs_ids:
            flash(_("You can only edit books within your libraries."), "danger")
            return redirect(url_for('main.home'))

    # The form needs to be instantiated before it can be populated
    form = BookForm(obj=book)

    # --- Populate Library Choices ---
    if current_user.role == 'admin':
        form.library.choices = [
            (lib.id, lib.name)
            for lib in Library.query.order_by('name').all()
        ]
    else:  # manager
        form.library.choices = [
            (lib.id, lib.name) for lib in current_user.libraries
        ]

    if request.method == 'GET':
        # Pre-fill form data for fields not handled by obj=book
        form.author.data = ", ".join([author.name for author in book.authors])
        form.library.data = book.library_id

        # Pre-fill location data if it exists
        if book.location:
            form.shelf.data = book.location.shelf
            form.section.data = book.location.section
            form.room.data = book.location.room
            form.location_notes.data = book.location.notes

    if form.validate_on_submit():
        # Update book fields from form data
        book.isbn = form.isbn.data
        book.title = form.title.data
        book.year = form.year.data
        book.library_id = form.library.data  # Update library

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

        book.genres.clear()
        selected_genres = form.genres.data
        book.genres.extend(selected_genres)

        # Handle cover update
        if form.cover.data:
            if isinstance(form.cover.data, FileStorage):
                f = form.cover.data
                cover_filename = secure_filename(f.filename)
                f.save(os.path.join(
                    current_app.config["UPLOAD_FOLDER"], cover_filename))
                book.cover = cover_filename

        # Handle location update
        if any([form.shelf.data, form.section.data, form.room.data, form.location_notes.data]):
            if book.location:
                # Update existing location
                book.location.shelf = form.shelf.data or None
                book.location.section = form.section.data or None
                book.location.room = form.room.data or None
                book.location.notes = form.location_notes.data or None
            else:
                # Create new location
                location = Location(
                    book_id=book.id,
                    shelf=form.shelf.data or None,
                    section=form.section.data or None,
                    room=form.room.data or None,
                    notes=form.location_notes.data or None
                )
                db.session.add(location)
        elif book.location:
            # Delete location if all fields are empty
            db.session.delete(book.location)

        db.session.commit()
        flash(_("Book updated successfully!"), "success")
        return redirect(url_for("main.home"))

    # Render template for GET request or form validation error
    return render_template("book_edit.html", form=form, book=book, active_page="books", title=_("Edit Book"))


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
    return redirect(url_for('books.book_detail', book_id=book.id))
