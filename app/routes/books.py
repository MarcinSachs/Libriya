import os
import secrets
import requests
from urllib.parse import urlparse
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file, jsonify
from flask_login import login_required, current_user
from flask_babel import gettext as _
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from PIL import Image
from io import BytesIO

from app import db, csrf
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
from app.services.openlibrary_service import OpenLibraryClient
from app.services.premium.manager import PremiumManager

bp = Blueprint("books", __name__)


@bp.route("/api/book/genres-from-isbn", methods=['POST'])
@csrf.exempt
def get_genres_from_isbn():
    """
    AJAX endpoint to fetch and map genres from Open Library for a given ISBN.

    Returns JSON with list of genre IDs and genre names.
    """
    try:
        # Debug info
        current_app.logger.info(f"Genres API - Request received")
        current_app.logger.info(f"Genres API - Content-Type: {request.content_type}")
        current_app.logger.info(f"Genres API - Raw data length: {len(request.data)}")

        # Try to get JSON data
        try:
            data = request.get_json(force=True)
        except Exception as e:
            current_app.logger.error(f"Genres API - JSON parse error: {e}")
            return jsonify({'error': 'Invalid JSON'}), 400

        current_app.logger.info(f"Genres API - Received JSON data: {data}")

        if not data:
            current_app.logger.error("Genres API - No JSON data received")
            return jsonify({'error': 'Invalid request'}), 400

        isbn = data.get('isbn', '').strip() if data else ''
        current_app.logger.info(f"Genres API - Extracted ISBN: '{isbn}'")

        if not isbn:
            current_app.logger.warning("Genres API - ISBN is empty or missing")
            return jsonify({'error': 'ISBN is required'}), 400

        try:
            # Try premium metadata services (like Biblioteka Narodowa) first
            current_app.logger.info(f"Genres API - Searching premium services for ISBN: {isbn}")
            book_data = PremiumManager.call('biblioteka_narodowa', 'search_by_isbn', isbn=isbn)

            if not book_data:
                # Fallback to Open Library
                current_app.logger.info(f"Genres API - Premium services failed, searching OL for ISBN: {isbn}")
                book_data = OpenLibraryClient.search_by_isbn(isbn)
                current_app.logger.info(f"Genres API - Book data from OL: {book_data is not None}")

            if not book_data:
                current_app.logger.warning(f"Genres API - Book not found for ISBN: {isbn}")
                return jsonify({'error': 'Book not found'}), 404

            # Check if we got genres from premium service or need to map from OL subjects
            genres_info = []

            # If book_data has 'genres' key, it's from premium service
            if 'genres' in book_data and book_data['genres']:
                current_app.logger.info(
                    f"Genres API - Found {len(book_data['genres'])} genres from premium service: {book_data['genres']}")
                # Map genre names to IDs
                for genre_name in book_data['genres']:
                    genre = Genre.query.filter_by(name=genre_name).first()
                    if genre:
                        genres_info.append({'id': genre.id, 'name': genre.name})
                        current_app.logger.info(f"Genres API - Mapped '{genre_name}' to ID {genre.id}")
                    else:
                        current_app.logger.warning(f"Genres API - Genre '{genre_name}' not found in database")
            else:
                # Get subjects from Open Library and map them
                subjects = book_data.get('subjects', [])
                current_app.logger.info(f"Genres API - Found {len(subjects)} subjects from OL: {subjects}")

                if not subjects:
                    current_app.logger.info(f"Genres API - No subjects found for ISBN: {isbn}")
                    return jsonify({
                        'genres': [],
                        'message': 'No subjects found for this book'
                    }), 200

                # Map OL subjects to application genres
                genre_ids = OpenLibraryClient.get_genre_ids_for_subjects(subjects)
                current_app.logger.info(f"Genres API - Mapped {len(genre_ids)} genre IDs: {genre_ids}")

                # Get genre names for display
                if genre_ids:
                    genres = Genre.query.filter(Genre.id.in_(genre_ids)).all()
                    genres_info = [{'id': g.id, 'name': g.name} for g in genres]
                    current_app.logger.info(f"Genres API - Genre info: {genres_info}")

            current_app.logger.info(f"Genres API - Success! Returning {len(genres_info)} genres")
            return jsonify({
                'genres': genres_info,
                'message': 'Genres automatically mapped from book metadata'
            }), 200

        except Exception as e:
            current_app.logger.error(f"Genres API - Error fetching genres: {e}", exc_info=True)
            return jsonify({'error': 'Error fetching book data'}), 500

    except Exception as e:
        current_app.logger.error(f"Genres API - Unexpected error: {e}", exc_info=True)
        return jsonify({'error': 'Unexpected error'}), 500


@bp.route("/api/book/genres-from-isbn/test", methods=['POST'])
@csrf.exempt
def get_genres_from_isbn_test():
    """
    Test endpoint without authentication for debugging.
    """
    try:
        current_app.logger.info(f"Test Genres API - Content-Type: {request.content_type}")
        current_app.logger.info(f"Test Genres API - Raw data: {request.data}")

        data = request.get_json(force=True)
        current_app.logger.info(f"Test Genres API - Received JSON data: {data}")

        if not data:
            return jsonify({'error': 'Invalid request', 'debug': 'No JSON data'}), 400

        isbn = data.get('isbn', '').strip() if data else ''
        current_app.logger.info(f"Test Genres API - Extracted ISBN: '{isbn}'")

        return jsonify({'success': True, 'isbn': isbn, 'debug': 'Test endpoint working'}), 200

    except Exception as e:
        current_app.logger.error(f"Test Genres API - Unexpected error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


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

    return render_template("books/book_detail.html", book=book, active_page="books",
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
        # Try to get description from form, or from Open Library/BN if available
        description = form.description.data.strip() if form.description.data else None

        # Try to fetch description from APIs if not provided
        if not description and form.isbn.data:
            # Try BN first
            book_data = PremiumManager.call('biblioteka_narodowa', 'search_by_isbn', isbn=form.isbn.data)
            if not book_data:
                book_data = OpenLibraryClient.search_by_isbn(form.isbn.data)
            if book_data:
                current_app.logger.info(f"[DEBUG] BN/OL book_data for ISBN {form.isbn.data}: {book_data}")
            if book_data and book_data.get('description'):
                description = book_data['description']
                current_app.logger.info(f"[DEBUG] Set description for ISBN {form.isbn.data}: {description}")

        new_book = Book(
            isbn=form.isbn.data,
            title=form.title.data,
            year=form.year.data,
            library_id=form.library.data,  # Assign library
            status='available',
            description=description
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

        # Handle cover image
        if form.cover.data:
            # User uploaded a file directly
            f = form.cover.data
            _, f_ext = os.path.splitext(f.filename)
            cover_filename = secrets.token_hex(8) + f_ext
            f.save(os.path.join(current_app.config["UPLOAD_FOLDER"], cover_filename))
            new_book.cover = cover_filename
        elif form.cover_url.data:
            # Cover URL from API search (hidden field)
            cover_url = form.cover_url.data.strip()

            try:
                if not cover_url:
                    current_app.logger.info("Cover URL is empty")
                # If cover_url is already cached locally (from API), just use the filename
                elif '/static/uploads/' in cover_url:
                    cover_filename = cover_url.split('/')[-1]
                    current_app.logger.info(f"Local cover found: {cover_filename}")
                    if cover_filename and cover_filename not in ['', '.', '..']:
                        new_book.cover = cover_filename
                        current_app.logger.info(f"Set book.cover to: {cover_filename}")
                # If cover_url is just a number (cover_id), convert to Open Library URL
                elif cover_url.isdigit():
                    cover_url = f"https://covers.openlibrary.org/b/id/{cover_url}-M.jpg"
                    current_app.logger.info(f"Converted cover_id to URL: {cover_url}")

                # Download external URL
                if cover_url and '/static/uploads/' not in cover_url and cover_url.startswith(('http://', 'https://')):
                    current_app.logger.info(f"Downloading external cover: {cover_url}")
                    response = requests.get(cover_url, stream=True, timeout=10)
                    response.raise_for_status()

                    if response.status_code == 200:
                        content = b''
                        for chunk in response.iter_content(chunk_size=1024):
                            content += chunk
                            if len(content) > 5 * 1024 * 1024:
                                raise ValueError("File too large")

                        _, f_ext = os.path.splitext(urlparse(cover_url).path)
                        if not f_ext or f_ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif']:
                            f_ext = '.jpg'
                        cover_filename = secrets.token_hex(8) + f_ext

                        picture_path = os.path.join(current_app.config["UPLOAD_FOLDER"], cover_filename)
                        with open(picture_path, 'wb') as f:
                            f.write(content)
                        new_book.cover = cover_filename
                        current_app.logger.info(f"Downloaded and saved cover: {cover_filename}")
            except Exception as e:
                current_app.logger.warning(f"Could not download cover: {e}")
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

        flash(BOOK_ADDED % {'title': new_book.title}, "success")
        return redirect(url_for("main.home"))

    return render_template("books/book_add.html", form=form)


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

    # Delete cover file if exists
    if book.cover:
        cover_path = os.path.join(current_app.config["UPLOAD_FOLDER"], book.cover)
        if os.path.exists(cover_path) and os.path.isfile(cover_path):
            try:
                os.remove(cover_path)
                current_app.logger.info(f"Deleted cover file: {book.cover}")
            except OSError as e:
                current_app.logger.warning(f"Could not delete cover file {book.cover}: {e}")

    # Log book deletion before removing it
    log_book_deleted(book.id, book.title)

    db.session.delete(book)
    db.session.commit()
    flash(BOOK_DELETED % {'title': book.title}, "success")
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
        book.description = form.description.data.strip() if form.description.data else None

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
        flash(BOOK_UPDATED % {'title': book.title}, "success")
        return redirect(url_for("main.home"))

    # Render template for GET request or form validation error
    return render_template("books/book_edit.html", form=form, book=book, active_page="books", title=_("Edit Book"))


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


@bp.route("/api/books/<int:book_id>/cover/micro")
def get_cover_micro(book_id):
    """
    Get micro-thumbnail version of book cover for PWA offline bulk caching.
    Returns highly compressed 50x75px image (~2-5KB) for minimal storage.
    Used for offline mode where bandwidth/storage is critical.
    """
    book = Book.query.get_or_404(book_id)

    if not book.cover:
        return {'error': 'No cover image'}, 404

    try:
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(book.cover))

        if not os.path.exists(file_path):
            current_app.logger.warning(f"Cover file not found: {file_path}")
            return {'error': 'Cover file not found'}, 404

        img = Image.open(file_path)

        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background

        # Create micro thumbnail: 50x75px (very small for bulk caching)
        img.thumbnail((50, 75), Image.Resampling.LANCZOS)

        # High compression JPEG quality 60 (~2-5KB per image)
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=60, optimize=True)
        buffer.seek(0)

        response = send_file(
            buffer,
            mimetype='image/jpeg',
            as_attachment=False,
            download_name=f'micro_{book_id}.jpg'
        )
        # Long cache - micro thumbnails rarely change
        response.headers['Cache-Control'] = 'public, max-age=604800'  # 7 days
        return response

    except Exception as e:
        current_app.logger.error(f"Error generating micro thumbnail for book {book_id}: {e}")
        return {'error': 'Error generating micro thumbnail'}, 500


@bp.route("/api/offline/books")
@login_required
def get_offline_books_data():
    """
    Get all books data for offline caching.
    Returns JSON with book metadata and micro-thumbnail URLs.
    Used by PWA to pre-cache all books for offline access.
    """
    try:
        # Admin gets all books, others get only books from their libraries
        if current_user.role == 'admin':
            books = Book.query.all()
        else:
            user_library_ids = [lib.id for lib in current_user.libraries]
            books = Book.query.filter(Book.library_id.in_(user_library_ids)).all()

        books_data = []
        for book in books:
            book_data = {
                'id': book.id,
                'title': book.title,
                'isbn': book.isbn,
                'year': book.year,
                'authors': [{'id': a.id, 'name': a.name} for a in book.authors],
                'library_id': book.library_id,
                'library_name': book.library.name if book.library else None,
                'has_cover': bool(book.cover),
                'cover_url': f'/static/uploads/{book.cover}' if book.cover else None,
                'micro_cover_url': f'/api/books/{book.id}/cover/micro' if book.cover else None,
                'detail_url': f'/book/{book.id}'
            }
            books_data.append(book_data)

        return {
            'success': True,
            'count': len(books_data),
            'books': books_data,
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        current_app.logger.error(f"Error getting offline books data: {e}")
        return {'success': False, 'error': str(e)}, 500
