from flask_wtf import FlaskForm
from wtforms import (
    StringField, SubmitField, IntegerField, PasswordField,
    SelectField, SelectMultipleField, TextAreaField, HiddenField
)
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo, Optional, ValidationError, NumberRange
)
from datetime import datetime
from flask_babel import lazy_gettext as _, gettext as _real
from app.models import Genre


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
            key=lambda x: x[1]
        )

        self.genres.choices = sorted_translated_genres
        if 'obj' in kwargs and kwargs['obj'] is not None:
            self.genres.data = [g.id for g in kwargs['obj'].genres]


class UserForm(FlaskForm):
    username = StringField(_('Username'), validators=[DataRequired()])
    email = StringField(_('Email'), validators=[DataRequired(), Email()],
                        render_kw={'placeholder': _('user@example.com')})  # Translated placeholder in forms.py
    password = PasswordField(_('Password'), validators=[DataRequired()])
    confirm_password = PasswordField(_('Confirm Password'), validators=[
                                     DataRequired(), EqualTo('password')])
    submit = SubmitField(_('Add User'), render_kw={"class": "btn btn-primary"})


class UserEditForm(FlaskForm):
    username = StringField(_('Username'), render_kw={'readonly': True})
    email = StringField(_('Email'), validators=[DataRequired(), Email()])
    role = SelectField(_('Role'), choices=[
        ('user', 'User'),
        ('manager', 'Manager'),
        ('admin', 'Admin')
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
    password = PasswordField(_('New Password'), validators=[Optional()])
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


class LoanForm(FlaskForm):
    book_id = SelectField(
        _('Book'),
        coerce=int,
        validators=[DataRequired()]
    )
    user_id = SelectField(
        _('User'),
        coerce=int,
        validators=[DataRequired()]
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


class RegistrationForm(FlaskForm):
    invitation_code = StringField(
        _('Invitation Code'),
        validators=[DataRequired(), Length(min=8, max=8)]
    )
    email = StringField(
        _('Email'),
        validators=[DataRequired(), Email()]
    )
    username = StringField(
        _('Username'),
        validators=[DataRequired(), Length(min=3, max=50)]
    )
    first_name = StringField(
        _('First Name'),
        validators=[DataRequired(), Length(min=2, max=50)]
    )
    last_name = StringField(
        _('Last Name'),
        validators=[DataRequired(), Length(min=2, max=50)]
    )
    password = PasswordField(
        _('Password'),
        validators=[DataRequired(), Length(min=8)]
    )
    password_confirm = PasswordField(
        _('Confirm Password'),
        validators=[DataRequired(), EqualTo('password')]
    )
    submit = SubmitField(_('Register'))

    def validate_invitation_code(self, field):
        from app.models import InvitationCode
        code = InvitationCode.query.filter_by(code=field.data).first()
        if not code:
            raise ValidationError(_('Invalid invitation code'))
        if not code.is_valid():
            raise ValidationError(_('Invitation code has expired or has already been used'))

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data).first()
        if user:
            raise ValidationError(_('Email already registered'))

    def validate_username(self, field):
        user = User.query.filter_by(username=field.data).first()
        if user:
            raise ValidationError(_('Username already taken'))


# Formularz kontaktowy
class ContactForm(FlaskForm):
    library = SelectField(_('Biblioteka'), coerce=int, validators=[DataRequired()])
    subject = StringField(_('Temat'), validators=[DataRequired(), Length(max=200)])
    message = TextAreaField(_('Wiadomość'), validators=[DataRequired(), Length(max=2000)])
    submit = SubmitField(_('Wyślij'))
