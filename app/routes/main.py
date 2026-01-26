import re
import requests
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, make_response, jsonify, session
from flask_login import login_required, current_user
from flask_babel import _, ngettext
from sqlalchemy import or_

from app import db
from app.models import Book, Genre, Notification, User

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


@bp.context_processor
def inject_unread_notifications_count():
    if current_user.is_authenticated:
        unread_count = Notification.query.filter_by(
            recipient=current_user, is_read=False).count()
        return {'unread_notifications_count': unread_count}
    return {'unread_notifications_count': 0}
