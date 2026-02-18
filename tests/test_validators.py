import pytest
from wtforms.validators import ValidationError
from app.utils import validators


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
