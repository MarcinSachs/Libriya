from app.utils.validators import validate_username_field, validate_email_field, sanitize_string, validate_subdomain_field
from app.models import Genre
from flask_babel import lazy_gettext as _, gettext as _real
from datetime import datetime
from app.utils.password_validator import validate_password_field
from flask_wtf import FlaskForm
from wtforms import (
    StringField, SubmitField, IntegerField, PasswordField,
    SelectField, SelectMultipleField, TextAreaField, HiddenField
)
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo, Optional, ValidationError, NumberRange
)
# Batch import form


class BatchImportForm(FlaskForm):
    isbn_list = TextAreaField(
        _('ISBN numbers (one per line or comma-separated)'),
        validators=[DataRequired(message=_('Please provide at least one ISBN.'))]
    )
    library = SelectField(
        _('Library'),
        coerce=int,
        validators=[DataRequired()]
    )
    submit = SubmitField(_('Import Books'))


class ISBNValidator:
    """Validator for ISBN-10 and ISBN-13 formats."""

    def __init__(self, message=None):
        self.message = (
            message or _('Invalid ISBN format. Must be 10 or 13 digits.')
        )

    def __call__(self, form, field):
        if field.data:
            # Remove hyphens and spaces
            isbn = field.data.replace('-', '').replace(' ', '')

            # Check if it's all digits
            if not isbn.isdigit():
                raise ValidationError(self.message)

            # Check length (ISBN-10 or ISBN-13)
            if len(isbn) not in [10, 13]:
                raise ValidationError(self.message)


class BookForm(FlaskForm):
    isbn = StringField(
        _('ISBN'),
        validators=[Optional(), ISBNValidator()]
    )
    title = StringField(_('Title'), validators=[DataRequired()])
    author = StringField(
        _('Author(s) (comma-separated)'),
        validators=[DataRequired()]
    )
    library = SelectField(
        _('Library'),
        coerce=int,
        validators=[DataRequired()]
    )
    genres = SelectMultipleField(
        _('Genres'),
        coerce=int,
        validators=[DataRequired()]
    )
    year = IntegerField(
        _('Year'),
        validators=[
            DataRequired(message=_("Field 'Year' is required.")),
            NumberRange(
                min=0,
                max=datetime.now().year,
                message=_("Please enter a valid year (e.g. 1999).")
            )
        ]
    )
    description = TextAreaField(
        _('Description'),
        validators=[Optional(), Length(max=2000)]
    )
    cover = FileField(
        _('Cover'),
        validators=[
            FileAllowed(
                ['jpg', 'png', 'jpeg'],
                _('Only image files (jpg, png, jpeg) are allowed!')
            )
        ]
    )
    # Hidden field to preserve cover URL on form validation errors
    cover_url = HiddenField(_('Cover URL'))

    # Location fields (optional)
    shelf = StringField(_('Shelf'), validators=[Optional(), Length(max=50)])
    section = StringField(_('Section'), validators=[Optional(), Length(max=100)])
    room = StringField(_('Room'), validators=[Optional(), Length(max=100)])
    location_notes = StringField(_('Location Notes'), validators=[Optional(), Length(max=255)])

    submit = SubmitField(_('Submit'), render_kw={"class": "btn btn-primary"})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        all_genres = Genre.query.all()

        translated_genres = [(g.id, _real(g.name)) for g in all_genres]
        sorted_translated_genres = sorted(
            translated_genres,
            key=lambda x: x[0]  # Sort by ID, not by name
        )

        self.genres.choices = sorted_translated_genres
        if 'obj' in kwargs and kwargs['obj'] is not None:
            self.genres.data = [g.id for g in kwargs['obj'].genres]

    def validate_title(self, field):
        field.data = sanitize_string(field.data, max_length=200)

    def validate_description(self, field):
        if field.data:
            field.data = sanitize_string(field.data, max_length=2000)


class UserForm(FlaskForm):
    username = StringField(_('Username'), validators=[DataRequired(), Length(min=3, max=50), validate_username_field])
    email = StringField(_('Email'), validators=[DataRequired(), validate_email_field],
                        render_kw={'placeholder': _('user@example.com')})  # Translated placeholder in forms.py
    password = PasswordField(_('Password'), validators=[DataRequired(), validate_password_field])
    confirm_password = PasswordField(_('Confirm Password'), validators=[
                                     DataRequired(), EqualTo('password')])
    submit = SubmitField(_('Add User'), render_kw={"class": "btn btn-primary"})


class UserEditForm(FlaskForm):
    username = StringField(_('Username'), render_kw={'readonly': True})
    email = StringField(_('Email'), validators=[DataRequired(), validate_email_field])
    role = SelectField(_('Role'), choices=[
        ('user', _('User')),
        ('manager', _('Manager')),
        ('admin', _('Admin'))
    ], validators=[DataRequired()])
    submit = SubmitField(_('Submit'), render_kw={
                         "class": "btn btn-primary"})


class UserSettingsForm(FlaskForm):
    email = StringField(_('Email'), validators=[DataRequired(), Email()])
    picture = FileField(_('Update Profile Picture'), validators=[
        FileAllowed(['jpg', 'png'], _('Images only!')),
        FileSize(max_size=2 * 1024 * 1024,
                 message=_('File size must be less than 2MB.'))
    ])
    password = PasswordField(_('New Password'), validators=[Optional(), validate_password_field])
    confirm_password = PasswordField(
        _('Confirm New Password'),
        validators=[EqualTo('password', message=_('Passwords must match.'))]
    )
    submit = SubmitField(_('Submit'), render_kw={
                         "class": "btn btn-primary"})


class LibraryForm(FlaskForm):
    name = StringField(_('Library Name'), validators=[DataRequired()])
    loan_overdue_days = IntegerField(_('Loan overdue days'), default=14, validators=[DataRequired()])
    submit = SubmitField(_('Submit'), render_kw={"class": "btn btn-primary"})

    def validate_name(self, field):
        field.data = sanitize_string(field.data, max_length=100)


class LoanForm(FlaskForm):
    book_id = SelectField(
        _('Book'),
        coerce=int,
        validators=[DataRequired()],
        validate_choice=False
    )
    user_id = SelectField(
        _('User'),
        coerce=int,
        validators=[DataRequired()],
        validate_choice=False
    )
    submit = SubmitField(
        _('Submit'),
        render_kw={"class": "btn btn-primary"}
    )


class CommentForm(FlaskForm):
    text = TextAreaField(
        _('Your Comment'),
        validators=[DataRequired(), Length(min=1, max=500)],
        render_kw={"rows": 8}
    )
    submit = SubmitField(_('Add Comment'))

    def validate_text(self, field):
        field.data = sanitize_string(field.data, max_length=500)


class RegistrationForm(FlaskForm):
    # Field to track whether user is creating a new tenant or joining existing one
    create_new_tenant = HiddenField(default='false')

    # For creating new tenant on main domain
    tenant_name = StringField(
        _('Organization Name'),
        validators=[Optional(), Length(min=3, max=100)]
    )

    # For joining existing tenant on subdomain
    invitation_code = StringField(
        _('Invitation Code'),
        validators=[Optional(), Length(min=8, max=8)]
    )

    email = StringField(
        _('Email'),
        validators=[DataRequired(), validate_email_field]
    )
    username = StringField(
        _('Username'),
        validators=[DataRequired(), Length(min=3, max=50), validate_username_field]
    )
    password = PasswordField(
        _('Password'),
        validators=[DataRequired(), Length(min=8)]
    )
    password_confirm = PasswordField(
        _('Confirm Password'),
        validators=[DataRequired(), EqualTo('password')]
    )
    first_name = StringField(
        _('First Name'),
        validators=[Optional(), Length(min=1, max=50)]
    )
    last_name = StringField(
        _('Last Name'),
        validators=[Optional(), Length(min=1, max=50)]
    )

    def validate_tenant_name(self, field):
        # Only validate if user is creating new tenant and field has data
        if self.create_new_tenant.data == 'true' and field.data:
            from app.models import Tenant
            existing = Tenant.query.filter_by(name=field.data).first()
            if existing:
                raise ValidationError(_('Library name already exists'))

    def validate_invitation_code(self, field):
        # Only validate if user is joining existing tenant and field has data
        if self.create_new_tenant.data == 'false' and field.data:
            from app.models import InvitationCode
            code = InvitationCode.query.filter_by(code=field.data).first()
            if not code:
                raise ValidationError(_('Invalid invitation code'))
            if not code.is_valid():
                raise ValidationError(_('Invitation code has expired or has already been used'))

    def validate_first_name(self, field):
        # Sanitize input and require first name when joining existing tenant
        field.data = sanitize_string(field.data, max_length=50)
        # treat empty or whitespace-only values as missing
        joining_existing = (
            str(self.create_new_tenant.data).lower() == 'false' or
            bool(getattr(self, 'invitation_code', None) and str(self.invitation_code.data).strip())
        )
        if joining_existing and (not field.data or not str(field.data).strip()):
            raise ValidationError(_('First name is required'))

    def validate_last_name(self, field):
        # Sanitize input and require last name when joining existing tenant
        field.data = sanitize_string(field.data, max_length=50)
        # treat empty or whitespace-only values as missing
        joining_existing = (
            str(self.create_new_tenant.data).lower() == 'false' or
            bool(getattr(self, 'invitation_code', None) and str(self.invitation_code.data).strip())
        )
        if joining_existing and (not field.data or not str(field.data).strip()):
            raise ValidationError(_('Last name is required'))

    def validate_email(self, field):
        from app.models import User
        user = User.query.filter_by(email=field.data).first()
        if user:
            raise ValidationError(_('Email already registered'))

    def validate_username(self, field):
        from app.models import User
        user = User.query.filter_by(username=field.data).first()
        if user:
            raise ValidationError(_('Username already taken'))

    def validate(self, *args, **kwargs):
        """Run standard validation then enforce first/last name when joining an existing tenant.
        This complements the per-field validators and ensures the form is correct
        even if input population differs between request/formdata and `data=`.
        """
        valid = super().validate(*args, **kwargs)

        inv_code = getattr(self, 'invitation_code', None).data if getattr(
            self, 'invitation_code', None) is not None else None
        has_code = bool(inv_code and str(inv_code).strip())
        joining_existing = (
            str(getattr(self, 'create_new_tenant', None).data).lower() == 'false' or
            has_code
        )

        if joining_existing:
            # Ensure first_name/last_name present when joining an existing tenant
            if not (self.first_name.data and str(self.first_name.data).strip()):
                self.first_name.errors.append(_('First name is required'))
                valid = False
            if not (self.last_name.data and str(self.last_name.data).strip()):
                self.last_name.errors.append(_('Last name is required'))
                valid = False

        return valid


# Formularz kontaktowy
class ContactForm(FlaskForm):
    library = SelectField(_('Library'), coerce=int, validators=[DataRequired()])
    subject = StringField(_('Subject'), validators=[DataRequired(), Length(max=200)])
    message = TextAreaField(_('Message'), validators=[DataRequired(), Length(max=2000)])
    submit = SubmitField(_('Send'))

    def validate_subject(self, field):
        field.data = sanitize_string(field.data, max_length=200)

    def validate_message(self, field):
        field.data = sanitize_string(field.data, max_length=2000)


# Formularz tenantu
class TenantForm(FlaskForm):
    name = StringField(
        _('Tenant Name'),
        validators=[DataRequired(), Length(min=2, max=100)]
    )
    subdomain = StringField(
        _('Subdomain'),
        validators=[DataRequired(), validate_subdomain_field],
        description=_('URL-friendly name (e.g., "mylib"). Only lowercase letters, numbers and hyphens.')
    )

    max_libraries = IntegerField(
        _('Max Libraries'),
        validators=[Optional()],
        description=_('Maximum number of libraries (leave blank or -1 for unlimited)')
    )
    max_books = IntegerField(
        _('Max Books'),
        validators=[Optional()],
        description=_('Maximum number of books (leave blank or -1 for unlimited)')
    )
    submit = SubmitField(_('Save Tenant'))

    # Per-field validation now uses `validate_subdomain_field` in validators.py

    def __init__(self, *args, **kwargs):
        # capture object being edited so we can ignore it during uniqueness checks
        self._original_id = None
        # keep a reference to the object on the form; some validators rely on form.obj
        self.obj = kwargs.get('obj', None)
        if self.obj is not None:
            try:
                self._original_id = self.obj.id
            except Exception:
                pass
        super().__init__(*args, **kwargs)

    def validate_name(self, field):
        """Validate tenant name uniqueness"""
        # Sanitize tenant name before validation
        field.data = sanitize_string(field.data, max_length=100)
        from app.models import Tenant
        existing = Tenant.query.filter_by(name=field.data).first()
        if existing:
            # if we're editing an existing tenant, allow the same name
            if self._original_id is not None and existing.id == self._original_id:
                return
            raise ValidationError(_('This tenant name already exists.'))
