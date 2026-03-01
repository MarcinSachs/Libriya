import io
from datetime import datetime
import pytest
from werkzeug.datastructures import FileStorage, MultiDict
from werkzeug.test import EnvironBuilder
from wtforms import Form
from wtforms.validators import ValidationError

from app.forms import (
    BookForm, ISBNValidator, UserForm, UserEditForm,
    UserSettingsForm, RegistrationForm, TenantForm, LibraryForm,
    CommentForm, LoanForm
)
from app.utils.password_validator import is_strong_password
from app import db
from app.models import Genre, Library, Tenant, InvitationCode, User


def test_is_strong_password_basic():
    ok, reasons = is_strong_password('weak')
    assert not ok
    assert reasons

    ok, reasons = is_strong_password('Str0ngPass!23')
    assert ok and reasons == []


def test_isbn_validator_direct():
    validator = ISBNValidator()

    class Dummy:
        pass

    field = Dummy()
    field.data = 'invalid-isbn'

    with pytest.raises(ValidationError):
        validator(None, field)

    field.data = '0-306-40615-2'  # valid ISBN-10
    # should not raise
    validator(None, field)


def test_bookform_validates_year_and_required_fields(app):
    with app.app_context():
        # prepare DB choices
        g = Genre(name='Fiction')
        db.session.add(g)
        # library must belong to a tenant (tenant_id NOT NULL)
        tenant = Tenant(name='LibTenant', subdomain='lt')
        db.session.add(tenant)
        db.session.commit()

        lib = Library(name='LibTest', tenant_id=tenant.id)
        db.session.add(lib)
        db.session.commit()

        data = {
            'isbn': '9780306406157',
            'title': 'Valid Title',
            'author': 'A. Author',
            'library': lib.id,
            'genres': [str(g.id)],
            'year': 1999,
            'description': 'OK'
        }

        # WTForms (and Flask-Babel) require a request context for translations
        with app.test_request_context('/'):
            form = BookForm(data=data)
            # the view normally sets library choices
            form.library.choices = [(lib.id, lib.name)]
            assert form.validate()

            # invalid year (future)
            future = datetime.now().year + 10
            form2 = BookForm(data={**data, 'year': future})
            form2.library.choices = [(lib.id, lib.name)]
            assert not form2.validate()
            assert form2.year.errors

            # the isbn field should filter out whitespace and convert to None
            form3 = BookForm(data={**data, 'isbn': '   '})
            form3.library.choices = [(lib.id, lib.name)]
            assert form3.validate()
            assert form3.isbn.data is None


def test_userform_password_strength(app):
    with app.app_context():
        # WTForms translations need a request context
        with app.test_request_context('/'):
            # weak password should fail form validation
            form = UserForm(data={'username': 'u', 'email': 'u@example.com',
                            'password': 'weakpass', 'confirm_password': 'weakpass'})
            assert not form.validate()

            # strong password passes (username must be >= 3 chars)
            form2 = UserForm(data={'username': 'user2', 'email': 'user2@example.com',
                             'password': 'Str0ngPass!23', 'confirm_password': 'Str0ngPass!23'})
            assert form2.validate()


def test_registrationform_tenant_name_and_invitation_logic(app):
    with app.app_context():
        # existing tenant -> validation should fail when creating new tenant with same name
        t = Tenant(name='ExistingTenant', subdomain='ex')
        db.session.add(t)
        db.session.commit()

        # Call the per-field validator directly to isolate tenant-name validation
        with app.test_request_context('/'):
            form = RegistrationForm()
            form.create_new_tenant.data = 'true'
            form.tenant_name.data = 'ExistingTenant'
            with pytest.raises(ValidationError):
                RegistrationForm.validate_tenant_name(form, form.tenant_name)

        # invitation code validation + required names when joining existing tenant
        invite = InvitationCode(code='ABCD1234', created_by_id=1, library_id=1, tenant_id=1)
        db.session.add(invite)
        db.session.commit()

        with app.test_request_context('/'):
            form2 = RegistrationForm(data={'create_new_tenant': 'false', 'invitation_code': 'ABCD1234', 'email': 'b@b.com',
                                     'username': 'usery', 'password': 'Str0ngPass!23', 'password_confirm': 'Str0ngPass!23', 'first_name': '', 'last_name': ''})
            assert not form2.validate()
            assert form2.first_name.errors and form2.last_name.errors

            # valid join (supply names)
            form3 = RegistrationForm(data={'create_new_tenant': 'false', 'invitation_code': 'ABCD1234', 'email': 'c@b.com', 'username': 'userz',
                                     'password': 'Str0ngPass!23', 'password_confirm': 'Str0ngPass!23', 'first_name': 'John', 'last_name': 'Doe'})
            assert form3.validate()


def test_tenantform_name_unique(app):
    with app.app_context():
        t = Tenant(name='UniqueTest', subdomain='uni')
        db.session.add(t)
        db.session.commit()

        with app.test_request_context('/'):
            form = TenantForm(data={'name': 'UniqueTest', 'subdomain': 'uni2'})
            assert not form.validate()
            assert form.name.errors


def test_libraryform_and_user_settings_file_validation(app):
    with app.app_context():
        form = LibraryForm(data={'name': 'MyLib', 'loan_overdue_days': 14})
        assert form.validate()

        # UserSettingsForm - simulate file upload and size
        fs = io.BytesIO(b'x' * (3 * 1024 * 1024))  # 3MB
        fs.name = 'large.jpg'
        # file validators run during form.validate(); create a dummy MultiDict is complex here,
        # so ensure the FileField validators are the expected objects exist on the form
        usf = UserSettingsForm()
        assert hasattr(usf, 'picture')
        assert hasattr(usf, 'language')
        # there should be at least one language choice (en/pl)
        assert usf.language.choices


def test_user_settings_picture_file_validation(app):
    with app.app_context():
        with app.test_request_context('/'):
            usf = UserSettingsForm(data={'email': 'me@example.com'})

            small_file = FileStorage(stream=io.BytesIO(b'x' * 1024), filename='small.jpg', content_type='image/jpeg')
            usf.picture.data = small_file
            assert usf.validate()  # small image should pass FileAllowed/FileSize

            large_file = FileStorage(stream=io.BytesIO(b'x' * (3 * 1024 * 1024)),
                                     filename='large.jpg', content_type='image/jpeg')
            usf2 = UserSettingsForm(data={'email': 'me2@example.com'})
            usf2.picture.data = large_file
            assert not usf2.validate()
            assert usf2.picture.errors


def test_bookform_cover_file_validation(app):
    with app.app_context():
        tenant = Tenant(name='CoverTenant', subdomain='ct')
        db.session.add(tenant)
        db.session.commit()
        lib = Library(name='CoverLib', tenant_id=tenant.id)
        db.session.add(lib)
        db.session.commit()

        g = Genre(name='G')
        db.session.add(g)
        db.session.commit()

        with app.test_request_context('/'):
            data = {
                'isbn': '9780306406157',
                'title': 'T',
                'author': 'A',
                'library': lib.id,
                'genres': [str(g.id)],
                'year': 2000,
                'description': 'd'
            }
            form = BookForm(data=data)
            form.library.choices = [(lib.id, lib.name)]

            ok_file = FileStorage(stream=io.BytesIO(b'x' * 1024), filename='cover.png', content_type='image/png')
            form.cover.data = ok_file
            assert form.validate()

            bad_ext = FileStorage(stream=io.BytesIO(b'x' * 1024), filename='cover.exe',
                                  content_type='application/octet-stream')
            form2 = BookForm(data=data)
            form2.library.choices = [(lib.id, lib.name)]
            form2.cover.data = bad_ext
            assert not form2.validate()
            assert form2.cover.errors


def test_registrationform_email_and_username_uniqueness(app):
    with app.app_context():
        existing = User(username='taken', email='taken@example.com')
        existing.set_password('doesntmatter')
        db.session.add(existing)
        db.session.commit()

        with app.test_request_context('/'):
            # duplicate username
            form = RegistrationForm(data={'create_new_tenant': 'true', 'tenant_name': 'New', 'email': 'new@example.com', 'username': 'taken',
                                    'password': 'Str0ngPass!23', 'password_confirm': 'Str0ngPass!23', 'first_name': 'A', 'last_name': 'B'})
            assert not form.validate()
            assert form.username.errors

            # duplicate email
            form2 = RegistrationForm(data={'create_new_tenant': 'true', 'tenant_name': 'New2', 'email': 'taken@example.com',
                                     'username': 'unique', 'password': 'Str0ngPass!23', 'password_confirm': 'Str0ngPass!23', 'first_name': 'A', 'last_name': 'B'})
            assert not form2.validate()
            assert form2.email.errors


def test_tenantform_subdomain_validation(app):
    with app.app_context():
        Tenant(name='TSub', subdomain='ts').save if False else None
        t = Tenant(name='ExistingSub', subdomain='exist')
        db.session.add(t)
        db.session.commit()

        with app.test_request_context('/'):
            # invalid subdomain (too short)
            form = TenantForm(data={'name': 'X', 'subdomain': 'ab'})
            assert not form.validate()
            assert form.subdomain.errors

            # reserved/duplicate
            form2 = TenantForm(data={'name': 'Y', 'subdomain': 'exist'})
            assert not form2.validate()
            assert form2.subdomain.errors

            # valid candidate
            form3 = TenantForm(data={'name': 'Good', 'subdomain': 'good-sub'})
            assert form3.validate()


def test_comment_and_loan_forms_sanitization_and_required(app):
    from app.forms import CommentForm, LoanForm
    with app.test_request_context('/'):
        # CommentForm: sanitize/length
        long_text = 'x' * 600
        cf = CommentForm(data={'text': long_text})
        assert not cf.validate()  # exceeds 500

        cf2 = CommentForm(data={'text': 'Normal text'})
        assert cf2.validate()

        # LoanForm requires both fields
        lf = LoanForm(data={})
        assert not lf.validate()

        lf2 = LoanForm(data={'book_id': 1, 'user_id': 1})
        assert lf2.validate()


def test_tenantform_name_unique_on_edit(app):
    """Editing a tenant should not trip the unique-name validator if the name is unchanged."""
    with app.app_context():
        t = Tenant(name='UniqueTest', subdomain='uni')
        other = Tenant(name='Other', subdomain='oth')
        db.session.add_all([t, other])
        db.session.commit()

        # editing `t` but leaving the name alone should validate
        with app.test_request_context('/'):
            form = TenantForm(obj=t, data={'name': 'UniqueTest', 'subdomain': 'uni'})
            assert form.validate(), form.errors

        # editing `t` and trying to rename it to an existing tenant's name should fail
        with app.test_request_context('/'):
            # sanity check that the other tenant is still in the database
            assert Tenant.query.filter_by(name='Other').first() is not None
            form2 = TenantForm(formdata=MultiDict({'name': 'Other', 'subdomain': 'uni'}), obj=t)
            # ensure the field actually picked up the new name
            assert form2.name.data == 'Other', f"name data was {form2.name.data!r}"
            existing = Tenant.query.filter_by(name=form2.name.data).first()
            assert existing is not None, "no tenant found with the submitted name"
            assert existing.id == other.id, f"existing id {existing.id} != other.id {other.id}"
            rv = form2.validate()
            # print errors for debugging if something goes wrong
            if rv:
                print('DEBUG: form2 validated unexpectedly, errors', form2.errors)
                print('field data', form2.name.data, form2.subdomain.data, 'original_id', form2._original_id)
            assert not rv
            assert form2.name.errors


# End of form tests
