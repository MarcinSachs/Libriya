import pytest
from wtforms.validators import ValidationError

from app.forms import ISBNValidator


class Dummy:
    pass


@pytest.mark.parametrize("isbn", [
    '0-306-40615-2',    # valid ISBN-10 with hyphens
    '0306406152',       # valid ISBN-10 digits only
    '9780306406157',    # valid ISBN-13 digits only
    '978-0-306-40615-7',# valid ISBN-13 with hyphens
    '978 0 306 40615 7' # valid ISBN-13 with spaces
])
def test_isbn_validator_accepts_valid_isbns(isbn):
    validator = ISBNValidator()
    field = Dummy()
    field.data = isbn

    # should not raise for known-good ISBNs
    validator(None, field)


@pytest.mark.parametrize("isbn", [
    '123',               # too short
    'abcdefghijk',       # non-digits
    '030640615',         # 9 chars (too short for ISBN-10)
    '03064061522',       # 11 chars (invalid length)
    '978030640615',      # 12 chars (invalid length)
    '97803064061570',    # 14 chars (invalid length)
    '0-306-40615-X',     # ISBN-10 with 'X' check-digit (not accepted by current validator)
    '978030640615X',     # non-digit in ISBN-13
    '0-306-40615-2a'     # trailing non-digit
])
def test_isbn_validator_rejects_invalid_isbns(isbn):
    validator = ISBNValidator()
    field = Dummy()
    field.data = isbn

    with pytest.raises(ValidationError):
        validator(None, field)


@pytest.mark.parametrize("isbn", ["", None])
def test_isbn_validator_allows_empty_or_none(isbn):
    """Validator should be a no-op for empty/None values (field optional)."""
    validator = ISBNValidator()
    field = Dummy()
    field.data = isbn

    # should not raise
    validator(None, field)
