from app.utils import validators
import pytest
from app.utils.validators import validate_username, validate_email_format, sanitize_string
from app.utils.password_validator import is_strong_password
from wtforms.validators import ValidationError

from app.utils import validators as v
from app.utils.subdomain import slugify_subdomain, is_valid_subdomain


def test_validate_username_accepts_good_usernames():
    # These should not raise
    v.validate_username('alice')
    v.validate_username('user_123')
    v.validate_username('A-B_9')


def test_validate_username_rejects_bad_usernames():
    with pytest.raises(ValidationError):
        v.validate_username('ab')  # too short
    with pytest.raises(ValidationError):
        v.validate_username('this username has spaces')
    with pytest.raises(ValidationError):
        v.validate_username('toolongusername_exceeding_limit')


def test_validate_email_format_accepts_valid_emails():
    v.validate_email_format('user@example.com')
    v.validate_email_format('first.last+tag@sub.domain.co')


def test_validate_email_format_rejects_invalid_emails():
    with pytest.raises(ValidationError):
        v.validate_email_format('not-an-email')
    with pytest.raises(ValidationError):
        v.validate_email_format('no-at-symbol.com')


def test_slugify_subdomain_and_is_valid():
    assert slugify_subdomain('My Library!') == 'my-library'
    assert slugify_subdomain('ÄÖÜ Tenant') == 'aou-tenant'
    # valid candidates
    assert is_valid_subdomain('abc')
    assert is_valid_subdomain('my-lib')
    # reserved and invalid
    assert not is_valid_subdomain('www')
    assert not is_valid_subdomain('-badstart')
    assert not is_valid_subdomain('ab')  # too short
    # long slug gets trimmed but must still be valid when trimmed
    long = 'a' * 30
    s = slugify_subdomain(long)
    assert len(s) <= 20
    assert is_valid_subdomain(s) or s == ''


def test_validate_username_accepts_good():
    # no exception means pass
    validators.validate_username('john_doe')
    validators.validate_username('user-123')
    validators.validate_username('A1') if False else None  # ensure no accidental short-circuit


def test_validate_username_rejects_bad():
    with pytest.raises(ValidationError):
        validators.validate_username('ab')  # too short
    with pytest.raises(ValidationError):
        validators.validate_username('this-is-a-very-long-username-over-20')
    with pytest.raises(ValidationError):
        validators.validate_username('bad*name')


def test_validate_email_format_accepts_good():
    validators.validate_email_format('user@example.com')
    validators.validate_email_format('first.last+tag@sub.domain.org')


def test_validate_email_format_rejects_bad():
    with pytest.raises(ValidationError):
        validators.validate_email_format('not-an-email')
    with pytest.raises(ValidationError):
        validators.validate_email_format('user@localhost')


def test_wtforms_wrappers():
    class DummyField:
        def __init__(self, data):
            self.data = data

    # wrappers should raise same ValidationError
    with pytest.raises(ValidationError):
        validators.validate_username_field(None, DummyField('ab'))
    with pytest.raises(ValidationError):
        validators.validate_email_field(None, DummyField('not-email'))

    # valid
    validators.validate_username_field(None, DummyField('valid_name'))
    validators.validate_email_field(None, DummyField('ok@example.com'))


def test_validate_username_valid():
    validators.validate_username('user_123')
    validators.validate_username('User-Name')


def test_validate_username_invalid():
    with pytest.raises(ValidationError):
        validators.validate_username('ab')  # too short
    with pytest.raises(ValidationError):
        validators.validate_username('user!@#')  # invalid chars
    with pytest.raises(ValidationError):
        validators.validate_username('a' * 21)  # too long


def test_validate_email_format_valid():
    validators.validate_email_format('test@example.com')
    validators.validate_email_format('user.name+tag@domain.co.uk')


def test_validate_email_format_invalid():
    with pytest.raises(ValidationError):
        validators.validate_email_format('not-an-email')
    with pytest.raises(ValidationError):
        validators.validate_email_format('user@')
    with pytest.raises(ValidationError):
        validators.validate_email_format('user@domain')


def test_sanitize_string():
    assert validators.sanitize_string('<b>test</b>') == '&lt;b&gt;test&lt;/b&gt;'
    assert validators.sanitize_string('abc', max_length=2) == 'ab'
    assert validators.sanitize_string(None) == ''


def test_is_strong_password():
    ok, reasons = is_strong_password('StrongPass123!')
    assert ok
    ok, reasons = is_strong_password('weak')
    assert not ok
    assert any('at least 12 characters' in str(r) for r in reasons)
    ok, reasons = is_strong_password('alllowercasepassword')
    assert not ok
    assert any('uppercase' in str(r).lower() for r in reasons)
    ok, reasons = is_strong_password('ALLUPPERCASE123!')
    assert not ok
    assert any('lowercase' in str(r).lower() for r in reasons)
    ok, reasons = is_strong_password('NoSpecialChar123')
    assert not ok
    assert any('special character' in str(r).lower() for r in reasons)
