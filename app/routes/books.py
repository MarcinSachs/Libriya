import os
import secrets
import requests
from urllib.parse import urlparse
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
from flask_login import login_required, current_user
from flask_babel import gettext as _
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from PIL import Image
from io import BytesIO

from app import db
from app.forms import BookForm
from app.models import Book, Author, Library, Location, Genre
from app.utils import role_required
from app.utils.audit_log import log_book_deleted
from app.utils.messages import (
    SUCCESS_CREATED, SUCCESS_UPDATED, SUCCESS_DELETED, ERROR_PERMISSION_DENIED,
    BOOK_ADDED, BOOK_UPDATED, BOOK_DELETED, ERROR_NOT_FOUND,
    COMMENT_ADDED, COMMENT_UPDATED, BOOK_ALREADY_IN_FAVORITES, BOOK_ADDED_TO_FAVORITES,
    BOOK_REMOVED_FROM_FAVORITES, BOOK_NOT_IN_FAVORITES, BOOK_CANNOT_DELETE_NOT_AVAILABLE,
    BOOKS_ONLY_EDIT_OWN_LIBRARIES, COVER_IMAGE_ERROR
)

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
            flash(COMMENT_UPDATED, 'success')
        else:
            new_comment = Comment(
                text=comment_form.text.data,
                book=book,
                user=current_user
            )
            db.session.add(new_comment)
            db.session.commit()
            flash(COMMENT_ADDED, 'success')

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

        # Add book to session first to avoid SQLAlchemy warnings
        db.session.add(new_book)

        selected_genres = form.genres.data
        if selected_genres:
            genres = Genre.query.filter(Genre.id.in_(selected_genres)).all()
            new_book.genres.extend(genres)

        if form.cover.data:
            f = form.cover.data
            cover_filename = secure_filename(f.filename)
            if cover_filename:
                f.save(os.path.join(
                    current_app.config["UPLOAD_FOLDER"], cover_filename))
                new_book.cover = cover_filename
            else:
                current_app.logger.warning("secure_filename returned empty for: " + f.filename)
        elif 'cover_url' in request.form and request.form['cover_url']:
            cover_url = request.form['cover_url'].strip()
            try:
                # Skip if URL is empty after stripping
                if not cover_url:
                    pass
                # If cover_url is already cached locally (from API), extract filename
                elif '/static/uploads/' in cover_url:
                    # Extract filename from path like "/static/uploads/abc123.jpg"
                    cover_filename = cover_url.split('/')[-1]
                    if cover_filename and cover_filename not in ['', '.', '..']:
                        new_book.cover = cover_filename
                # If cover_url is just a number (cover_id), convert to full Open Library URL
                elif cover_url.isdigit():
                    cover_url = f"https://covers.openlibrary.org/b/id/{cover_url}-M.jpg"
                    parsed_url = urlparse(cover_url)
                    if parsed_url.scheme not in ['http', 'https']:
                        raise ValueError(f"Invalid URL scheme. Only HTTP(S) allowed. Got: {parsed_url.scheme}")
                # If it's already a full URL, validate it
                elif cover_url.startswith('http://') or cover_url.startswith('https://'):
                    parsed_url = urlparse(cover_url)
                    if parsed_url.scheme not in ['http', 'https']:
                        raise ValueError(f"Invalid URL scheme. Only HTTP(S) allowed. Got: {parsed_url.scheme}")
                else:
                    # Unknown format, skip cover download
                    pass

                # Only proceed if we have a valid URL (not already handled above)
                if cover_url and not '/static/uploads/' in cover_url and (cover_url.startswith('http://') or cover_url.startswith('https://')):
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
                error_msg = f"Could not download cover image: {str(e)}"
                flash(error_msg, "danger")

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

        flash(BOOK_ADDED, "success")
        return redirect(url_for("main.home"))

    return render_template("book_add.html", form=form)


@bp.route("/book_delete/<int:book_id>", methods=["POST"])
@login_required
@role_required('admin', 'manager')
def book_delete(book_id):
    book = Book.query.get_or_404(book_id)

    # --- Authorization ---
    if current_user.role == 'manager':
        user_libs_ids = [lib.id for lib in current_user.libraries]
        if book.library_id not in user_libs_ids:
            flash(BOOKS_ONLY_EDIT_OWN_LIBRARIES, "danger")
            return redirect(url_for('main.home'))

    # Prevent deletion if the book has any associated loans (active or past)
    if book.status != 'available':
        flash(BOOK_CANNOT_DELETE_NOT_AVAILABLE % {'title': book.title, 'status': book.status}, "danger")
        return redirect(url_for("main.home"))

    # Log book deletion before removing it
    log_book_deleted(book.id, book.title)

    db.session.delete(book)
    db.session.commit()
    flash(BOOK_DELETED, "success")
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
            flash(BOOKS_ONLY_EDIT_OWN_LIBRARIES, "danger")
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
        if selected_genres:
            genres = Genre.query.filter(Genre.id.in_(selected_genres)).all()
            book.genres.extend(genres)

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
        flash(BOOK_UPDATED, "success")
        return redirect(url_for("main.home"))

    # Render template for GET request or form validation error
    return render_template("book_edit.html", form=form, book=book, active_page="books", title=_("Edit Book"))


@bp.route('/favorites/add/<int:book_id>', methods=['POST'])
@login_required
def add_favorite(book_id):
    user = current_user
    book = Book.query.get_or_404(book_id)
    if book in user.favorites:
        flash(BOOK_ALREADY_IN_FAVORITES, 'info')
    else:
        user.favorites.append(book)
        db.session.commit()
        flash(BOOK_ADDED_TO_FAVORITES, 'success')
    return redirect(url_for('main.home'))


@bp.route('/favorites/remove/<int:book_id>', methods=['POST'])
@login_required
def remove_favorite(book_id):
    user = current_user
    book = Book.query.get_or_404(book_id)
    if book in user.favorites:
        user.favorites.remove(book)
        db.session.commit()
        flash(BOOK_REMOVED_FROM_FAVORITES, 'success')
    else:
        flash(BOOK_NOT_IN_FAVORITES, 'info')
    return redirect(url_for('books.book_detail', book_id=book.id))


@bp.route("/api/cleanup-cover", methods=["POST"])
@login_required
def cleanup_cover():
    """
    Remove temporary cover file when user cancels adding/editing a book.

    Expected JSON: {"cover_url": "filename or URL"}
    """
    try:
        data = request.get_json()
        cover_url = data.get('cover_url', '').strip()

        if not cover_url:
            return {'success': False, 'error': 'No cover URL provided'}, 400

        # Only delete local files, not external URLs
        # Extract filename from path if it's a local file
        if '/' in cover_url:
            filename = cover_url.split('/')[-1]
        else:
            filename = cover_url

        # Security: only allow alphanumeric and common image extensions
        if not all(c.isalnum() or c in '._-' for c in filename):
            return {'success': False, 'error': 'Invalid filename'}, 400

        file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)

        # Extra security: ensure path is within UPLOAD_FOLDER
        real_upload_folder = os.path.realpath(current_app.config["UPLOAD_FOLDER"])
        real_file_path = os.path.realpath(file_path)
        if not real_file_path.startswith(real_upload_folder):
            return {'success': False, 'error': 'Invalid file path'}, 403

        # Delete the file if it exists
        if os.path.exists(file_path) and os.path.isfile(file_path):
            os.remove(file_path)
            return {'success': True, 'message': 'Cover file deleted'}

        return {'success': True, 'message': 'File does not exist (already deleted)'}

    except Exception as e:
        current_app.logger.error(f"Error cleaning up cover: {e}")
        return {'success': False, 'error': str(e)}, 500


@bp.route("/api/books/<int:book_id>/cover/thumbnail")
def get_cover_thumbnail(book_id):
    """
    Get thumbnail version of book cover for PWA offline caching.
    Returns compressed 200x300px image (~40KB) instead of full-size (~200KB).
    Useful for offline PWA to cache more cover images without excessive storage.
    """
    book = Book.query.get_or_404(book_id)

    if not book.cover:
        return {'error': 'No cover image'}, 404

    try:
        # Construct file path
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(book.cover))

        if not os.path.exists(file_path):
            current_app.logger.warning(f"Cover file not found: {file_path}")
            return {'error': 'Cover file not found'}, 404

        # Open and process image
        img = Image.open(file_path)

        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background

        # Create thumbnail: 200x300px (standard book cover ratio)
        img.thumbnail((200, 300), Image.Resampling.LANCZOS)

        # Compress to JPEG with quality 75 (40-50KB per image)
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=75, optimize=True)
        buffer.seek(0)

        # Return with proper cache headers (1 day cache)
        response = send_file(
            buffer,
            mimetype='image/jpeg',
            as_attachment=False,
            download_name=f'thumb_{book_id}.jpg'
        )
        response.headers['Cache-Control'] = 'public, max-age=86400'  # 24 hours
        return response

    except Exception as e:
        current_app.logger.error(f"Error generating thumbnail for book {book_id}: {e}")
        return {'error': 'Error generating thumbnail'}, 500
