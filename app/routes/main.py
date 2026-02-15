import re
import requests
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, make_response, jsonify, session, Response
from flask_login import login_required, current_user
from flask_babel import _, ngettext
from sqlalchemy import or_
import os

from app import db, csrf
from app.models import Book, Genre, Notification, User, ContactMessage, Author
from app.forms import ContactForm
from app.services.book_service import BookSearchService
from app.services.cover_service import CoverService
from app.utils.messages import (
    INFO_LANGUAGE_CHANGED_EN, INFO_LANGUAGE_CHANGED_PL,
    ERROR_UNSUPPORTED_LANGUAGE, ERROR_PERMISSION_DENIED, NOTIFICATION_MARKED_READ,
    NOTIFICATION_ALL_MARKED_READ
)

bp = Blueprint("main", __name__)


# --- KONTAKT ---
@bp.route('/contact', methods=['GET', 'POST'])
@login_required
def contact():
    """Redirect to my-messages for consistency"""
    return redirect(url_for('main.my_messages'))


@bp.route('/my-messages', methods=['GET', 'POST'])
@login_required
def my_messages():
    """View all contact messages sent by the current user and send new ones"""
    # Mark notification as read if notification_id is provided
    notification_id = request.args.get('notification_id', type=int)
    if notification_id:
        notification = Notification.query.get(notification_id)
        if notification and notification.recipient_id == current_user.id:
            notification.is_read = True
            db.session.commit()

    form = ContactForm()
    # Set available libraries for the user
    form.library.choices = [(lib.id, lib.name) for lib in current_user.libraries]

    if form.validate_on_submit():
        msg = ContactMessage(
            user_id=current_user.id,
            library_id=form.library.data,
            subject=form.subject.data,
            message=form.message.data
        )
        from app import db
        db.session.add(msg)
        db.session.commit()

        # Create notification for admins and library managers
        library = msg.library
        # Notify all admins
        admins = User.query.filter_by(role='admin').all()
        for admin in admins:
            notification = Notification(
                recipient_id=admin.id,
                sender_id=current_user.id,
                contact_message_id=msg.id,
                message=_('New contact message from library %(library)s', library=library.name),
                type='contact_message'
            )
            db.session.add(notification)

        # Notify library managers
        for manager in library.users:
            if manager.role == 'manager':
                notification = Notification(
                    recipient_id=manager.id,
                    sender_id=current_user.id,
                    contact_message_id=msg.id,
                    message=_('New contact message from library %(library)s', library=library.name),
                    type='contact_message'
                )
                db.session.add(notification)

        db.session.commit()
        flash(_('Message has been sent.'), 'success')
        return redirect(url_for('main.my_messages'))

    # Get all messages sent by current user
    messages = ContactMessage.query.filter_by(user_id=current_user.id).order_by(
        ContactMessage.created_at.desc()).all()

    return render_template('superadmin/my_messages.html', form=form, messages=messages, title=_('My Messages'))


@bp.route("/favicon.ico")
def favicon():
    return current_app.send_static_file("favicon.ico")


@bp.route("/offline")
def offline():
    """Offline page with translations"""
    return render_template("base/offline.html", title=_("Offline"))


@bp.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    return render_template("landing/landing.html", landing_page=True)


@bp.route("/index")
def index():
    return render_template("index.html")


@bp.route("/dashboard")
@login_required
def home():
    status_filter = request.args.get('status')
    genre_filter_id = request.args.get('genre', type=int)
    title_filter = request.args.get('title')
    sort_by = request.args.get('sort_by', 'title')  # Default sort by title

    query = Book.query

    # --- LOCATION BASED FILTERING ---
    if current_user.role != 'admin':
        user_library_ids = [lib.id for lib in current_user.libraries]
        if not user_library_ids:
            # If user is not in any library, show no books
            query = query.filter(Book.id == -1)  # a trick to return no results
        else:
            query = query.filter(Book.library_id.in_(user_library_ids))
    # --- END OF FILTERING ---

    if title_filter:
        # Search in title, description, and author names
        search_term = f"%{title_filter}%"
        query = query.outerjoin(Book.authors).filter(
            or_(
                Book.title.ilike(search_term),
                Book.description.ilike(search_term),
                Author.name.ilike(search_term)
            )
        ).distinct()

    if status_filter:
        if status_filter == 'available':
            query = query.filter(Book.status == 'available')
        elif status_filter == 'on_loan':
            query = query.filter(
                or_(Book.status == 'on_loan', Book.status == 'reserved'))

    if genre_filter_id:
        query = query.join(Book.genres).filter(Genre.id == genre_filter_id)

    # Apply sorting
    if sort_by == 'title':
        query = query.order_by(Book.title.asc())
    elif sort_by == 'title_desc':
        query = query.order_by(Book.title.desc())
    elif sort_by == 'year':
        query = query.order_by(Book.year.asc())
    elif sort_by == 'year_desc':
        query = query.order_by(Book.year.desc())
    else:
        query = query.order_by(Book.title.asc())

    books = query.all()
    genres = Genre.query.all()
    genres = sorted(genres, key=lambda g: _(g.name))

    # Numbers of unread notifications to layout
    unread_notifications_count = Notification.query.filter_by(
        recipient=current_user, is_read=False
    ).count()

    return render_template("books/index.html", books=books, genres=genres, active_page="books",
                           unread_notifications_count=unread_notifications_count)


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

    return render_template("superadmin/notifications.html", notifications=notifications, title=_("Your Notifications"),
                           unread_notifications_count=unread_notifications_count)


@bp.route("/notifications/mark_read/<int:notification_id>", methods=['POST'])
@login_required
def mark_notification_as_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)

    if notification.recipient_id != current_user.id and not current_user.is_admin:
        flash(ERROR_PERMISSION_DENIED, "danger")
        return redirect(url_for('main.view_notifications'))

    notification.is_read = True
    db.session.commit()
    flash(NOTIFICATION_MARKED_READ, "success")
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
    flash(NOTIFICATION_ALL_MARKED_READ, "success")
    return redirect(url_for('main.view_notifications'))


@bp.route('/set_language/<lang>')
def set_language(lang):
    if lang in current_app.config['LANGUAGES']:
        # Flash message BEFORE creating response (so it's in session)
        message = INFO_LANGUAGE_CHANGED_PL if lang == 'pl' else INFO_LANGUAGE_CHANGED_EN
        flash(message, 'info')

        # Create a response object from the redirect
        response = make_response(
            redirect(request.referrer or url_for('main.home')))

        # Set cookie for 2 years with explicit path
        response.set_cookie('language', lang, max_age=60*60*24*365*2, path='/')

        return response
    flash(ERROR_UNSUPPORTED_LANGUAGE, 'danger')
    return redirect(request.referrer or url_for('main.home'))


@bp.route("/api/v1/isbn/<isbn>", methods=["GET"])
@login_required
def get_book_by_isbn(isbn):
    """
    API endpoint to fetch book data by ISBN.

    Searches in Open Library API with optional premium source extensions.
    """
    try:
        current_app.logger.info(f"API /api/v1/isbn/ called with: {isbn}")

        book_data = BookSearchService.search_by_isbn(isbn=isbn)

        if not book_data:
            return jsonify({"error": _("No data found for this ISBN. Please check the number and try again.")}), 404

        # Format response for frontend
        response_data = {
            "title": book_data.get("title"),
            "author": ", ".join(book_data.get("authors", [])) if book_data.get("authors") else "",
            "year": book_data.get("year"),
            "isbn": book_data.get("isbn"),
            "publisher": book_data.get("publisher"),
            "source": book_data.get("source"),
            "description": book_data.get("description"),
        }

        # Add cover info with local caching for external URLs
        cover_info = book_data.get("cover", {})
        cover_url = None
        cover_source = "local_default"

        if isinstance(cover_info, dict):
            cover_url = cover_info.get("url")
            cover_source = cover_info.get("source", "local_default")
        else:
            cover_url = cover_info
            cover_source = "open_library"

        # Download and cache external cover URLs locally
        if cover_url and cover_source != "local_default" and cover_url.startswith(("http://", "https://")):
            try:
                uploaded_filename = CoverService.download_and_save_cover(
                    cover_url,
                    current_app.config['UPLOAD_FOLDER']
                )
                if uploaded_filename:
                    # Use local cached URL
                    response_data["cover_image"] = f"/static/uploads/{uploaded_filename}"
                    current_app.logger.info(f"Cached cover locally: {uploaded_filename}")
                else:
                    # Keep external URL as fallback
                    response_data["cover_image"] = cover_url
            except Exception as e:
                current_app.logger.warning(f"Failed to cache cover: {e}")
                response_data["cover_image"] = cover_url
        else:
            response_data["cover_image"] = cover_url

        response_data["cover_source"] = cover_source

        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"ISBN search error: {e}")
        return jsonify({"error": _("Error during search. Please try again.")}), 500


@bp.route("/api/v1/search/title", methods=["GET"])
@login_required
def search_book_by_title():
    """
    API endpoint to search for books by title.

    Searches in Open Library API with optional premium source extensions.

    Query params:
        - q (required): Search query (min 3 characters)
        - limit (optional): Max results (default: 10, max: 20)
        - author (optional): Filter by author
    """
    query = request.args.get('q', '').strip()
    author = request.args.get('author', '').strip()
    limit = request.args.get('limit', 10, type=int)

    if not query or len(query) < 3:
        return jsonify({"error": _("Search query must be at least 3 characters")}), 400

    try:
        results = BookSearchService.search_by_title(
            title=query,
            author=author or None,
            limit=min(limit, 20)
        )

        # Format for frontend
        formatted_results = []
        for book in results:
            formatted_book = {
                "title": book.get("title"),
                "authors": book.get("authors", []),
                "isbn": book.get("isbn"),
                "year": book.get("year"),
                "source": book.get("source"),
            }

            # Add cover info with local caching for external URLs
            cover_info = book.get("cover", {})
            cover_url = None
            cover_source = "local_default"

            if isinstance(cover_info, dict):
                cover_url = cover_info.get("url")
                cover_source = cover_info.get("source", "local_default")
            else:
                cover_url = cover_info
                cover_source = "open_library"

            # Download and cache external cover URLs locally
            if cover_url and cover_source != "local_default" and cover_url.startswith(("http://", "https://")):
                try:
                    uploaded_filename = CoverService.download_and_save_cover(
                        cover_url,
                        current_app.config['UPLOAD_FOLDER']
                    )
                    if uploaded_filename:
                        # Use local cached URL
                        formatted_book["cover_id"] = f"/static/uploads/{uploaded_filename}"
                        current_app.logger.debug(f"Cached cover locally: {uploaded_filename}")
                    else:
                        # Keep external URL as fallback
                        formatted_book["cover_id"] = cover_url
                except Exception as e:
                    current_app.logger.warning(f"Failed to cache cover: {e}")
                    formatted_book["cover_id"] = cover_url
            else:
                formatted_book["cover_id"] = cover_url

            formatted_book["cover_source"] = cover_source
            formatted_results.append(formatted_book)

        return jsonify({"results": formatted_results, "total": len(formatted_results)})

    except Exception as e:
        current_app.logger.error(f"Title search error: {e}")
        return jsonify({"error": _("Error during search. Please try again.")}), 500


@bp.context_processor
def inject_unread_notifications_count():
    if current_user.is_authenticated:
        unread_count = Notification.query.filter_by(
            recipient=current_user, is_read=False).count()
        return {'unread_notifications_count': unread_count}
    return {'unread_notifications_count': 0}


@bp.route('/debug/locale')
@login_required
def debug_locale():
    """Debug endpoint to check current locale and translations"""
    from flask_babel import get_locale
    from babel.core import Locale
    import os

    current_locale = get_locale()
    locale_name = str(current_locale)

    # Try to verify if messages catalog exists
    base_dir = current_app.root_path
    locale_path = os.path.join(base_dir, '../translations', locale_name, 'LC_MESSAGES', 'messages.mo')
    mo_exists = os.path.exists(locale_path)
    po_exists = os.path.exists(locale_path.replace('.mo', '.po'))

    return jsonify({
        "current_locale": locale_name,
        "current_locale_obj": str(current_locale),
        "cookie": request.cookies.get('language'),
        "session": session.get('language'),
        "accept_languages": str(request.accept_languages),
        "messages_mo_exists": mo_exists,
        "messages_po_exists": po_exists,
        "test_translation": _("Add a new book")
    })


@bp.route("/api/v1/ocr/isbn", methods=["POST"])
@csrf.exempt
@login_required
def ocr_isbn_from_image():
    """
    API endpoint to extract ISBN from image using OCR.
    Uses EasyOCR - pure Python, no system dependencies required.
    Works on Windows, Linux, and server environments.
    """
    try:
        if 'image' not in request.files:
            current_app.logger.debug(f"OCR: No 'image' in files. Keys: {list(request.files.keys())}")
            return jsonify({"success": False, "error": "No image provided"}), 400

        file = request.files['image']
        if file.filename == '':
            current_app.logger.debug("OCR: Empty filename")
            return jsonify({"success": False, "error": "No image selected"}), 400

        # Check file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Seek back to start

        if file_size == 0:
            current_app.logger.debug("OCR: Empty file (0 bytes)")
            return jsonify({"success": False, "error": "Empty image file"}), 400

        # Import here to catch import errors
        try:
            import cv2
            import numpy as np
            import easyocr
        except ImportError as e:
            current_app.logger.error(f"Missing OCR dependencies: {e}")
            return jsonify({
                "success": False,
                "error": "OCR engine not available"
            }), 503

        # Read image from bytes
        nparr = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return jsonify({"success": False, "error": "Invalid image"}), 400

# Preprocess image for better OCR - optimized for speed
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Increase contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Use Otsu's threshold - fast and effective for ISBN numbers
        _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Minimal morphological cleanup for speed
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # Try original enhanced image as well (sometimes better for thin text)
        images_to_try = [thresh, enhanced]  # Reduced from 4 to 2 for speed

        # Initialize EasyOCR reader (cached after first use)
        try:
            if not hasattr(current_app, '_ocr_reader'):
                current_app.logger.info("Initializing EasyOCR reader...")
                # Suppress PyTorch DataLoader warnings for CPU-only setup
                import warnings
                import torch
                warnings.filterwarnings('ignore', category=UserWarning, module='torch.utils.data.dataloader')
                torch.set_num_threads(1)  # Optimize for single-threaded use

                current_app._ocr_reader = easyocr.Reader(['en'], gpu=False)

            reader = current_app._ocr_reader

            # Try OCR on multiple preprocessed versions
            all_text = ""
            for idx, test_image in enumerate(images_to_try):
                try:
                    results = reader.readtext(test_image, detail=1)
                    # Lower confidence threshold for faster detection
                    text_parts = [detection[1] for detection in results if detection[2] > 0.15]
                    text = ' '.join(text_parts)
                    if text.strip():
                        all_text += " " + text
                        current_app.logger.debug(f"OCR attempt {idx+1}: {text[:80]}")
                except Exception as e:
                    current_app.logger.debug(f"OCR attempt {idx+1} failed: {e}")
                    continue

            text = all_text

        except Exception as ocr_err:
            current_app.logger.warning(f"OCR extraction failed: {ocr_err}")
            text = ""

        # Extract ISBN from text
        import re

        # Clean text - remove non-digits except X and dash
        cleaned = re.sub(r'[^\d\sX-]', '', text.upper())

        current_app.logger.info(f"OCR cleaned text: {cleaned[:150]}")

        # Try to find 13-digit ISBN first (can be with or without dashes)
        match13 = re.search(r'(\d{1,5})-?(\d{1,7})-?(\d{1,7})-?(\d)', cleaned)
        if match13:
            # Validate it's actually 13 digits
            isbn13_raw = match13.group(0).replace('-', '')
            if len(isbn13_raw) >= 10:
                current_app.logger.info(f"ISBN-13+ detected via OCR: {isbn13_raw}")
                return jsonify({"success": True, "isbn": isbn13_raw})

        # Try simple 13-digit sequence
        match13_simple = re.search(r'\d{13}', cleaned)
        if match13_simple:
            isbn = match13_simple.group()
            current_app.logger.info(f"ISBN-13 detected via OCR: {isbn}")
            return jsonify({"success": True, "isbn": isbn})

        # Try to find 10-digit ISBN with dashes (83-225-0046-7)
        match10_dash = re.search(r'(\d{2})-(\d{3})-(\d{4})-([X\d])', cleaned)
        if match10_dash:
            isbn10 = ''.join(match10_dash.groups())
            current_app.logger.info(f"ISBN-10 with dashes detected via OCR: {isbn10}")
            return jsonify({"success": True, "isbn": isbn10})

        # Try 10-digit ISBN without dashes
        match10 = re.search(r'\d{9}[X\d]', cleaned)
        if match10:
            isbn = match10.group()
            current_app.logger.info(f"ISBN-10 detected via OCR: {isbn}")
            return jsonify({"success": True, "isbn": isbn})

        # If no ISBN found
        current_app.logger.debug(f"No ISBN pattern found in OCR text. Raw text: {cleaned[:200]}")
        return jsonify({"success": False, "isbn": None})

    except Exception as e:
        current_app.logger.error(f"OCR API error: {e}", exc_info=True)
        return jsonify({"success": False, "error": "OCR processing failed"}), 500
