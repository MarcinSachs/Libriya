import re
from wtforms.validators import ValidationError
from flask_babel import lazy_gettext as _


def validate_username(username):
    """Validate username format.

    Raises ValidationError if invalid.
    """
    if not re.match(r'^[a-zA-Z0-9_-]{3,20}$', username):
        raise ValidationError(_('Username must be 3-20 chars, alphanumeric with - and _'))


def validate_email_format(email):
    """Validate email format.

    Raises ValidationError if invalid.
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValidationError(_('Invalid email format'))


def sanitize_string(text, max_length=None):
    """Escape HTML and optionally truncate string.

    Returns escaped string.
    """
    import html
    if text is None:
        return ''
    text = html.escape(str(text))
    if max_length:
        return text[:max_length]
    return text


# WTForms-compatible wrappers (callables receiving form, field)
def validate_username_field(form, field):
    """WTForms validator wrapper for username field."""
    validate_username(field.data)


def validate_email_field(form, field):
    """WTForms validator wrapper for email field."""
    validate_email_format(field.data)


def validate_subdomain_field(form, field):
    """WTForms validator wrapper for tenant subdomain field.

    Normalizes the candidate, validates format and uniqueness, and replaces
    `field.data` with the canonical slug when needed.
    """
    from app.utils.subdomain import is_valid_subdomain, slugify_subdomain
    from app.models import Tenant

    candidate = slugify_subdomain(field.data or '', max_length=20)

    # if we're editing and the value hasn't changed, just accept it; the
    # existing subdomain may already violate the current rules (e.g. two
    # characters) and we don't want to force an update just to pass validation.
    obj = getattr(form, 'obj', None)
    if obj is not None and getattr(obj, 'subdomain', None) == candidate:
        # still normalize the data so that forms display canonical slug
        field.data = candidate
        return

    if not is_valid_subdomain(candidate):
        raise ValidationError(_(
            'Subdomain can only contain lowercase letters, numbers, and hyphens, 3-20 chars, cannot start/end with hyphen.'
        ))

    # Check uniqueness
    existing = Tenant.query.filter_by(subdomain=candidate).first()
    if existing:
        if not obj or getattr(obj, 'id', None) != getattr(existing, 'id', None):
            raise ValidationError(_('This subdomain is already taken.'))

    # Replace with canonical slug
    field.data = candidate
