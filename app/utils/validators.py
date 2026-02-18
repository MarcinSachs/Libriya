import re
from wtforms.validators import ValidationError


def validate_username(username):
    """Validate username format.

    Raises ValidationError if invalid.
    """
    if not re.match(r'^[a-zA-Z0-9_-]{3,20}$', username):
        raise ValidationError('Username must be 3-20 chars, alphanumeric with - and _')


def validate_email_format(email):
    """Validate email format.

    Raises ValidationError if invalid.
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValidationError('Invalid email format')


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
