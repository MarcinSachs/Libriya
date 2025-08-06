from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, PasswordField, SelectField, BooleanField
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms.validators import DataRequired, NumberRange, Email, EqualTo, Optional
from datetime import datetime
from flask_babel import lazy_gettext as _
from app.models import Genre


class BookForm(FlaskForm):
    isbn = StringField('ISBN')
    title = StringField(_('Title'), validators=[DataRequired()])
    author = StringField(_('Author(s) (comma-separated)'),
                         validators=[DataRequired()])
    genre = SelectField(_('Genre'), coerce=int, validators=[
                        DataRequired()])
    year = IntegerField(
        _('Year'),
        validators=[
            DataRequired(message=_("Field 'Year' is required.")),
            NumberRange(min=0, max=datetime.now().year,
                        message=_("Please enter a valid year (e.g. 1999)."))
        ]
    )
    cover = FileField(_('Cover'), validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], _('Only image files (jpg, png, jpeg) are allowed!'))])
    # Added btn-primary class
    submit = SubmitField(_('Submit'), render_kw={"class": "btn btn-primary"})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        genres = Genre.query.all()

        translated_genres = [(g.id, _(g.name)) for g in genres]
        sorted_genres = sorted(translated_genres, key=lambda x: x[1])
        self.genre.choices = sorted_genres


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
    is_admin = BooleanField(_('Administrator privileges'))
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


class LoanForm(FlaskForm):
    book_id = SelectField(_('Book'), coerce=int, validators=[DataRequired()])
    user_id = SelectField(_('User'), coerce=int, validators=[DataRequired()])
    # Added btn-primary class
    submit = SubmitField(_('Submit'), render_kw={
                         "class": "btn btn-primary"})
