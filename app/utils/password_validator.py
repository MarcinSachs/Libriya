from wtforms.validators import ValidationError
from flask_babel import lazy_gettext as _
import re
import hashlib
import requests


class PasswordValidationError(ValueError):
    pass


def is_strong_password(password: str) -> (bool, list):
    """Check password strength rules.

    Returns (True, []) if pass, otherwise (False, [reasons]).
    Rules implemented:
      - Minimum 12 characters
      - Must contain upper, lower, digit, special
    """
    reasons = []
    if not password or len(password) < 12:
        reasons.append(_('Password must be at least 12 characters long.'))
    if not re.search(r'[A-Z]', password):
        reasons.append(_('Password must contain at least one uppercase letter.'))
    if not re.search(r'[a-z]', password):
        reasons.append(_('Password must contain at least one lowercase letter.'))
    if not re.search(r'[0-9]', password):
        reasons.append(_('Password must contain at least one digit.'))
    if not re.search(r'[\W_]', password):
        reasons.append(_('Password must contain at least one special character.'))
    return (len(reasons) == 0, reasons)


def check_pwned_password(password: str, timeout: float = 5.0) -> int:
    """Check password against haveibeenpwned API using k-anonymity.

    Returns the number of times the password was seen in breaches (0 means not found).
    Raises requests.RequestException on network errors.

    Note: This hashes the password with SHA1, sends the first 5 hex chars to the
    HIBP API and scans returned suffixes for a match.
    """
    if not password:
        return 0
    sha1 = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    prefix = sha1[:5]
    suffix = sha1[5:]
    url = f'https://api.pwnedpasswords.com/range/{prefix}'
    headers = {'User-Agent': 'Libriya-Password-Checker'}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    for line in resp.text.splitlines():
        parts = line.split(':')
        if len(parts) != 2:
            continue
        if parts[0].strip() == suffix:
            try:
                return int(parts[1].strip())
            except ValueError:
                return 1
    return 0


# WTForms helper


def validate_password_field(form, field):
    """WTForms validator to enforce password policy and optional pwned check.

    To enable HIBP check, set `app.config['ENABLE_PWNED_CHECK'] = True` and
    ensure the environment allows outbound HTTPS requests.
    """
    password = field.data or ''
    ok, reasons = is_strong_password(password)
    if not ok:
        raise ValidationError('\n'.join(reasons))

    # Optional pwned check
    app = None
    try:
        # import lazily to avoid circular import at module import time
        from flask import current_app
        app = current_app._get_current_object()
    except Exception:
        app = None

    enable_pwned = False
    if app:
        enable_pwned = app.config.get('ENABLE_PWNED_CHECK', False)

    if enable_pwned:
        try:
            count = check_pwned_password(password)
        except Exception:
            # Network failures shouldn't block registration; log elsewhere.
            count = 0
        if count > 0:
            raise ValidationError(_('This password has appeared in a data breach and cannot be used.'))
