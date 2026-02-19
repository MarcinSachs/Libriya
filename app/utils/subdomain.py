import re
import unicodedata
import secrets

RESERVED_SUBDOMAINS = {'www', 'localhost', '127', 'admin', 'api', 'mail'}

SUBDOMAIN_RE = re.compile(r'^[a-z0-9](?:[a-z0-9-]{1,18}[a-z0-9])?$')


def slugify_subdomain(value: str, max_length: int = 20) -> str:
    """Create a URL-friendly subdomain candidate from an arbitrary name.

    - Normalize unicode to ASCII
    - Lowercase
    - Replace non-alnum with hyphens
    - Collapse repeated hyphens
    - Trim to max_length and remove leading/trailing hyphens
    """
    if not value:
        return ''

    # Normalize Unicode chars to closest ASCII representation
    value = unicodedata.normalize('NFKD', value)
    value = value.encode('ascii', 'ignore').decode('ascii')
    value = value.lower()

    # Replace invalid characters with hyphen
    value = re.sub(r'[^a-z0-9]+', '-', value)

    # Collapse multiple hyphens
    value = re.sub(r'-{2,}', '-', value)

    # Trim
    value = value.strip('-')
    if len(value) > max_length:
        value = value[:max_length].rstrip('-')

    return value


def is_valid_subdomain(value: str) -> bool:
    """Return True if value is a valid subdomain according to rules.

    Rules:
    - Only lowercase letters, numbers and hyphens
    - Between 3 and 20 characters
    - Cannot start or end with hyphen
    - Not in RESERVED_SUBDOMAINS
    """
    if not value or not isinstance(value, str):
        return False
    if len(value) < 3 or len(value) > 20:
        return False
    if value in RESERVED_SUBDOMAINS:
        return False
    return bool(SUBDOMAIN_RE.match(value))


def unique_candidate(base: str, exists_fn, max_length: int = 20) -> str:
    """Generate a unique subdomain candidate based on base using exists_fn to check availability.

    Tries appending a numeric suffix if needed, otherwise falls back to random suffix.
    """
    base = slugify_subdomain(base, max_length)
    if not base:
        base = 'tenant'

    # If base is valid and not taken, return it
    if is_valid_subdomain(base) and not exists_fn(base):
        return base

    # Try numeric suffixes
    for i in range(1, 1000):
        suffix = f"-{i}"
        limit = max_length - len(suffix)
        candidate = (base[:limit].rstrip('-') + suffix)
        if is_valid_subdomain(candidate) and not exists_fn(candidate):
            return candidate

    # Fallback to random small token
    token = secrets.token_hex(3)
    limit = max_length - (len(token) + 1)
    candidate = (base[:limit].rstrip('-') + '-' + token)
    return candidate
