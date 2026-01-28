import re
import requests
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, make_response, jsonify, session, Response
from flask_login import login_required, current_user
from flask_babel import _, ngettext
from sqlalchemy import or_

from app import db
from app.models import Book, Genre, Notification, User
from app.services.book_service import BookSearchService
from app.services.cover_service import CoverService
from app.utils.messages import (
    INFO_LANGUAGE_CHANGED_EN, INFO_LANGUAGE_CHANGED_PL,
    ERROR_UNSUPPORTED_LANGUAGE, ERROR_PERMISSION_DENIED, NOTIFICATION_MARKED_READ,
    NOTIFICATION_ALL_MARKED_READ
)

bp = Blueprint("main", __name__)


@bp.route("/favicon.ico")
def favicon():
    return current_app.send_static_file("favicon.ico")


@bp.route("/")
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
        query = query.filter(Book.title.ilike(f"%{title_filter}%"))

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

    return render_template("index.html", books=books, genres=genres, active_page="books",
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

    return render_template("notifications.html", notifications=notifications, title=_("Your Notifications"),
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

    Searches in this priority:
    1. Biblioteka Narodowa (Polish National Library) - networks catalog
    2. Open Library API
    3. Enriches with cover from best available source

    Query params:
        - include_bn (bool): Include BN search (default: true)
    """
    try:
        current_app.logger.info(f"API /api/v1/isbn/ called with: {isbn}")
        use_bn = request.args.get('include_bn', 'true').lower() != 'false'

        book_data = BookSearchService.search_by_isbn(
            isbn=isbn,
            use_bn=use_bn,
            use_openlibrary=True
        )

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

    Searches in this priority:
    1. Biblioteka Narodowa (Polish National Library)
    2. Open Library API
    3. Merges results and enriches with covers

    Query params:
        - q (required): Search query (min 3 characters)
        - limit (optional): Max results (default: 10, max: 20)
        - author (optional): Filter by author
        - include_bn (bool): Include BN search (default: true)
    """
    query = request.args.get('q', '').strip()
    author = request.args.get('author', '').strip()
    limit = request.args.get('limit', 10, type=int)
    use_bn = request.args.get('include_bn', 'true').lower() != 'false'

    if not query or len(query) < 3:
        return jsonify({"error": _("Search query must be at least 3 characters")}), 400

    try:
        results = BookSearchService.search_by_title(
            title=query,
            author=author or None,
            limit=min(limit, 20),
            use_bn=use_bn,
            use_openlibrary=True
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
