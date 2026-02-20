from app.utils import validators
from wtforms.validators import ValidationError
from app.models import Tenant


def test_validate_subdomain_field_normalizes_and_sets_data(app):
    class DummyForm:
        pass

    class DummyField:
        def __init__(self, data):
            self.data = data

    f = DummyField('My Library!')
    validators.validate_subdomain_field(DummyForm(), f)
    assert f.data == 'my-library'


def test_validate_subdomain_field_rejects_invalid_and_reserved(app):
    class DummyForm:
        pass

    class DummyField:
        def __init__(self, data):
            self.data = data

    # too short
    with __import__('pytest').raises(ValidationError):
        validators.validate_subdomain_field(DummyForm(), DummyField('ab'))

    # reserved
    with __import__('pytest').raises(ValidationError):
        validators.validate_subdomain_field(DummyForm(), DummyField('www'))

    # invalid chars are normalized (not rejected) -> should be slugified
    f_bad = DummyField('Bad*Name')
    validators.validate_subdomain_field(DummyForm(), f_bad)
    assert f_bad.data == 'bad-name'


def test_validate_subdomain_field_uniqueness_and_edit_allows_same(app):
    # create existing tenant
    existing = Tenant(name='Exists', subdomain='exist')
    from app import db
    db.session.add(existing)
    db.session.commit()

    class DummyField:
        def __init__(self, data):
            self.data = data

    # new form (no obj) should raise for duplicate
    with __import__('pytest').raises(ValidationError):
        validators.validate_subdomain_field(object(), DummyField('exist'))

    # editing form that provides same tenant object should be allowed
    class EditForm:
        def __init__(self, obj):
            self.obj = obj

    f = DummyField('Exist')  # mixed case -> will be slugified
    validators.validate_subdomain_field(EditForm(existing), f)
    assert f.data == 'exist'