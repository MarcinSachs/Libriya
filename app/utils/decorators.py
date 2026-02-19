from functools import wraps
from flask import flash, redirect, url_for, request, abort
from flask_login import current_user
from flask_babel import _


def role_required(*roles):
    """Decorator to require specific user roles for a route."""
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Allow superadmin regardless of specific role checks
            if not current_user.is_authenticated or (current_user.role not in roles and not getattr(current_user, 'is_super_admin', False)):
                # For AJAX requests, return JSON
                if request.is_json or request.path.startswith('/admin/premium'):
                    from flask import jsonify
                    return jsonify({'error': _("You do not have the required privileges to access this page.")}), 403
                
                flash(
                    _("You do not have the required privileges to access this page."), "danger")
                return redirect(url_for('main.home'))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper


def tenant_required(f):
    """
    Dekorator sprawdzający czy użytkownik ma dostęp do tenantu
    Zapobiega dostępowi do innego tenantu niż jego własny
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)  # Unauthorized

        # Pobierz tenant z subdomeny
        host_parts = request.host.split(':')[0].split('.')

        if len(host_parts) > 1 and host_parts[0] not in ('localhost', 'www'):
            subdomain = host_parts[0]
            from app.models import Tenant
            tenant = Tenant.query.filter_by(subdomain=subdomain).first()

            # Sprawdź czy użytkownik należy do tego tenantu
            if not tenant or current_user.tenant_id != tenant.id:
                abort(403)  # Forbidden

        return f(*args, **kwargs)
    return decorated_function
