import re
import requests
import hashlib
from datetime import datetime
from math import ceil
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, make_response, jsonify, session, Response
from flask_login import login_required, current_user
from flask_babel import _, ngettext
from sqlalchemy import or_
from sqlalchemy.orm import joinedload, subqueryload
import os

from app import db, csrf, limiter, cache
from app.models import Book, Genre, Notification, User, ContactMessage, Author, Library
from app.forms import ContactForm
from app.services.book_service import BookSearchService
from app.services.cover_service import CoverService
from app.services.recommendation_service import RecommendationService
from app.services.cache_service import get_dashboard_cache_version
from app.utils.messages import (
    INFO_LANGUAGE_CHANGED_EN, INFO_LANGUAGE_CHANGED_PL,
    ERROR_UNSUPPORTED_LANGUAGE, ERROR_PERMISSION_DENIED, NOTIFICATION_MARKED_READ,
    NOTIFICATION_ALL_MARKED_READ
)

bp = Blueprint("main", __name__)


def make_dashboard_cache_key(user_scope, cache_version, title_filter, status_filter, genre_filter_id, library_filter_id, sort_by, page):
    key_parts = [
        user_scope,
        str(cache_version),
        title_filter or '',
        status_filter or '',
        str(genre_filter_id) if genre_filter_id is not None else '',
        str(library_filter_id) if library_filter_id is not None else '',
        sort_by or '',
        str(page)
    ]
    digest = hashlib.sha256('|'.join(key_parts).encode('utf-8')).hexdigest()
    return f'dashboard_query_{user_scope}_{cache_version}_{page}_{digest}'


class SimplePagination:
    def __init__(self, page, per_page, total, items):
        self.page = page
        self.per_page = per_page
        self.total = total
        self.items = items

    @property
    def pages(self):
        if not self.total:
            return 0
        return ceil(self.total / self.per_page)

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def prev_num(self):
        return self.page - 1 if self.has_prev else None

    def iter_pages(self, left_edge=1, right_edge=1, left_current=2, right_current=2):
        if self.pages == 0:
            return

        left_end = min(1 + left_edge, self.pages + 1)
        yield from range(1, left_end)

        if left_end > self.pages:
            return

        mid_start = max(left_end, self.page - left_current)
        mid_end = min(self.page + right_current + 1, self.pages + 1)

        if mid_start - left_end > 0:
            yield None

        yield from range(mid_start, mid_end)

        if mid_end > self.pages:
            return

        right_start = max(mid_end, self.pages + 1 - right_edge)
        if right_start - mid_end > 0:
            yield None

        yield from range(right_start, self.pages + 1)

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def next_num(self):
        return self.page + 1 if self.has_next else None


# --- HELPER FUNCTIONS ---


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

        # Audit: contact message sent
        try:
            from app.utils.audit_log import log_action
            log_action('CONTACT_MESSAGE_SENT', f'Contact message {msg.id} sent by {current_user.username}', subject=msg, additional_info={
                       'library_id': msg.library_id})
        except Exception:
            pass

        # Create notification for admins and library managers
        library = msg.library
        # Notify all tenant admins (scope to current tenant)
        admins = User.query.filter_by(role='admin', tenant_id=current_user.tenant_id).all()
        for admin in admins:
            notification = Notification(
                recipient_id=admin.id,
                sender_id=current_user.id,
                contact_message_id=msg.id,
                message=_('New contact message from library %(library)s', library=library.name),
                type='contact_message'
            )
            db.session.add(notification)

        # Notify library managers (users with manager role in this library)
        for membership in library.user_library_memberships:
            if membership.library_role == 'manager':
                manager = membership.user
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
    """Offline fallback page.  This is a very small standalone template that
    does not depend on external CSS/JS so that it can render even when the
    device is completely offline.
    """
    return render_template("base/offline.html")


@bp.route('/service-worker.js')
def service_worker():
    """Dynamically generate the service worker script so it can access
    configuration such as the cache version.

    This mirrors the old static file but allows us to render Jinja expressions
    inside the worker.
    """
    response = make_response(render_template('service-worker.js'))
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/'  # allow entire origin
    return response


# backward compatibility: redirect old static path to the dynamic endpoint
@bp.route('/static/service-worker.js')
def legacy_service_worker():
    return redirect(url_for('main.service_worker'), code=302)


# Legacy/root-level auth URLs used by some bookmarks or service workers
# (see mobile testing notes).  These simply redirect to the current
# auth blueprint rather than returning 404.
@bp.route("/login/", strict_slashes=False)
def legacy_login():
    return redirect(url_for('auth.login'))


@bp.route("/register/", strict_slashes=False)
def legacy_register():
    # registration page has two modes; we simply redirect to the generic
    # entry point, preserving query string if any
    return redirect(url_for('auth.register_choice'))


@bp.route("/")
@csrf.exempt
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    return render_template("landing/landing.html", landing_page=True)


@bp.route("/index")
def index():
    return render_template("index.html")


@bp.route("/dashboard")
@login_required
@limiter.limit("20 per minute")
def home():
    status_filter = request.args.get('status')
    genre_filter_id = request.args.get('genre', type=int)
    library_filter_id = request.args.get('library', type=int)
    title_filter = request.args.get('title')
    sort_by = request.args.get('sort_by', 'title')  # Default sort by title
    page = request.args.get('page', 1, type=int)
    per_page = 100

    if current_user.is_super_admin:
        user_scope = 'superadmin'
        cache_version = get_dashboard_cache_version(superadmin=True)
    elif current_user.role == 'admin':
        user_scope = f'tenant_{current_user.tenant_id}'
        cache_version = get_dashboard_cache_version(tenant_id=current_user.tenant_id)
    else:
        user_scope = f'user_{current_user.id}'
        cache_version = get_dashboard_cache_version(tenant_id=current_user.tenant_id)

    cache_key = make_dashboard_cache_key(
        user_scope, cache_version, title_filter, status_filter,
        genre_filter_id, library_filter_id, sort_by, page
    )
    cached_page = cache.get(cache_key)

    if cached_page is not None:
        book_ids = cached_page.get('ids', [])
        total_books = cached_page.get('total', 0)

        if book_ids:
            books = Book.query.options(
                joinedload(Book.library),
                subqueryload(Book.authors),
                subqueryload(Book.genres),
            ).filter(Book.id.in_(book_ids)).all()
            books_by_id = {book.id: book for book in books}
            books = [books_by_id[bid] for bid in book_ids if bid in books_by_id]
        else:
            books = []

        pagination = SimplePagination(page, per_page, total_books, books)
    else:
        query = Book.query

        # --- LOCATION BASED FILTERING ---
        if current_user.is_super_admin:
            pass  # superadmin sees all books across all tenants
        elif current_user.role == 'admin':
            # tenant admin sees all books within their tenant
            query = query.filter(Book.tenant_id == current_user.tenant_id)
        else:
            user_library_ids = [lib.id for lib in current_user.libraries]
            if not user_library_ids:
                # If user is not in any library, show no books
                query = query.filter(Book.id == -1)  # a trick to return no results
            else:
                query = query.filter(Book.library_id.in_(user_library_ids))
        # --- END OF FILTERING ---

        if library_filter_id:
            query = query.filter(Book.library_id == library_filter_id)

        if title_filter:
            # Search in title, description, and author names with stemming support
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

        pagination = query.options(
            joinedload(Book.library),
            subqueryload(Book.authors),
            subqueryload(Book.genres),
        ).paginate(page=page, per_page=per_page, error_out=False)

        books = pagination.items
        total_books = pagination.total

        cache.set(cache_key, {'ids': [book.id for book in books], 'total': total_books}, timeout=20)

    genres = Genre.query.all()
    genres = sorted(genres, key=lambda g: _(g.name))

    # Libraries visible to the current user (for library filter dropdown)
    if current_user.is_super_admin:
        user_libraries = Library.query.order_by(Library.name).all()
    elif current_user.role == 'admin':
        user_libraries = Library.query.filter_by(tenant_id=current_user.tenant_id).order_by(Library.name).all()
    else:
        user_libraries = sorted(current_user.libraries, key=lambda l: l.name)

    # Prepare recommendations (based on favorite books + description similarity)
    # Cache stores only book IDs (plain ints) to avoid SQLAlchemy DetachedInstanceError
    # when deserialising objects from Redis across worker processes.
    recommended_books = []
    if current_user.is_authenticated and current_user.favorites:
        cache_key = f'recs_{current_user.id}'
        lock_key = f'recs_lock_{current_user.id}'
        cached_ids = cache.get(cache_key)
        if cached_ids is not None:
            # Fast path: reload by primary key – always safe across all workers
            id_map = {b.id: b for b in Book.query.filter(Book.id.in_(cached_ids)).all()}
            recommended_books = [id_map[bid] for bid in cached_ids if bid in id_map]
        elif not cache.get(lock_key):
            # Only one worker computes at a time; others return empty list (page still loads)
            cache.set(lock_key, True, timeout=15)
            try:
                recommended_books = RecommendationService.get_recommendations_for_user(
                    current_user, max_results=4
                )
                cache.set(cache_key, [b.id for b in recommended_books], timeout=300)
            except Exception as exc:
                current_app.logger.warning(f'Recommendations failed: {exc}')
                recommended_books = []
            finally:
                cache.delete(lock_key)

    # Numbers of unread notifications to layout
    unread_notifications_count = Notification.query.filter_by(
        recipient=current_user, is_read=False
    ).count()

    favorite_book_ids = set()
    if current_user.is_authenticated and not current_user.is_anonymous:
        favorite_book_ids = {b.id for b in current_user.favorites}

    return render_template("books/index.html", books=books, genres=genres, active_page="books",
                           recommended_books=recommended_books,
                           favorite_book_ids=favorite_book_ids,
                           user_libraries=user_libraries,
                           unread_notifications_count=unread_notifications_count,
                           pagination=pagination,
                           total_books=total_books)


@bp.route("/api/v1/search", methods=['GET'])
@login_required
def api_search_books():
    """
    API endpoint for live search with dynamic filtering.
    Returns JSON with matching books.
    """
    search_query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 10, type=int)

    if len(search_query) < 2:
        return jsonify({'books': []})

    # Cache key scoped to user role/tenant so results are never leaked across tenants
    if current_user.is_super_admin:
        scope = 'superadmin'
    elif current_user.role == 'admin':
        scope = f't{current_user.tenant_id}'
    else:
        scope = f'u{current_user.id}'

    cache_key = f'search_{scope}_{search_query}_{limit}'
    cached = cache.get(cache_key)
    if cached is not None:
        return jsonify(cached)

    # Same filtering as home() route
    query = Book.query

    # --- LOCATION BASED FILTERING ---
    if current_user.is_super_admin:
        pass  # superadmin sees all books across all tenants
    elif current_user.role == 'admin':
        query = query.filter(Book.tenant_id == current_user.tenant_id)
    else:
        user_library_ids = [lib.id for lib in current_user.libraries]
        if not user_library_ids:
            return jsonify({'books': []})
        query = query.filter(Book.library_id.in_(user_library_ids))
    # --- END OF FILTERING ---

    # Search in title, description, and author names
    search_term = f"%{search_query}%"
    query = query.outerjoin(Book.authors).filter(
        or_(
            Book.title.ilike(search_term),
            Book.description.ilike(search_term),
            Author.name.ilike(search_term)
        )
    ).distinct().order_by(Book.title.asc()).limit(limit)

    books = query.all()

    # Convert to JSON-serializable format
    result = {
        'books': [
            {
                'id': book.id,
                'title': book.title,
                'author': ', '.join([a.display_name for a in book.authors]) if book.authors else 'Unknown',
                'description': (book.description[:100] + '...') if book.description and len(book.description) > 100 else book.description,
                'year': book.year,
                'status': book.status,
                'url': url_for('books.book_detail', book_id=book.id)
            }
            for book in books
        ]
    }

    cache.set(cache_key, result, timeout=30)
    return jsonify(result)


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

    # Audit: notification marked as read
    try:
        from app.utils.audit_log import log_action
        log_action('NOTIFICATION_MARKED_READ', f'Notification {notification_id} marked as read by {current_user.username}', subject=notification, additional_info={
                   'notification_id': notification_id})
    except Exception:
        pass

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

    # Audit: mark all notifications read
    try:
        from app.utils.audit_log import log_action
        log_action('NOTIFICATIONS_MARKED_ALL_READ',
                   f'All notifications marked read by {current_user.username}', subject=None)
    except Exception:
        pass

    flash(NOTIFICATION_ALL_MARKED_READ, "success")
    return redirect(url_for('main.view_notifications'))


@bp.route('/set_language/<lang>')
def set_language(lang):
    if lang in current_app.config['LANGUAGES']:
        # Flash message BEFORE creating response (so it's in session)
        message = INFO_LANGUAGE_CHANGED_PL if lang == 'pl' else INFO_LANGUAGE_CHANGED_EN
        flash(message, 'info')

        # if user is logged in, save preference to DB as well
        if current_user.is_authenticated:
            try:
                current_user.preferred_locale = lang
                db.session.commit()
            except Exception:
                db.session.rollback()

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

        isbn_cache_key = f'isbn_raw_{isbn}'
        book_data = cache.get(isbn_cache_key)
        if book_data is None:
            book_data = BookSearchService.search_by_isbn(isbn=isbn)
            if book_data:
                cache.set(isbn_cache_key, book_data, timeout=120)

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

        # Return cover image URL for preview only; do not download locally in the ISBN lookup API.
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

            # Return cover image URL for preview only; do not download locally in the title search API.
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


@bp.context_processor
def inject_pwa_settings():
    """Make cache version and pre‑cache list available to templates.

    The service worker itself is served by a dynamic route so it can see the
    same version string; other JavaScript code reads the global
    ``window.pwaConfig`` object.
    """
    current_user_id = current_user.id if current_user.is_authenticated else None
    return {
        'PWA_CACHE_VERSION': current_app.config.get('PWA_CACHE_VERSION', 'v1'),
        'PWA_PRECACHE_PAGES': current_app.config.get('PWA_PRECACHE_PAGES', []),
        'PWA_UPDATE_INTERVAL': current_app.config.get('PWA_UPDATE_INTERVAL', 300000),
        'PWA_CURRENT_USER_ID': current_user_id
    }


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
