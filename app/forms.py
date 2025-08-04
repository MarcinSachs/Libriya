from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, PasswordField, SelectField, BooleanField
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms.validators import DataRequired, NumberRange, Email, EqualTo, Optional
from datetime import datetime
from flask_babel import lazy_gettext as _


class BookForm(FlaskForm):
    isbn = StringField('ISBN')
    title = StringField('Title', validators=[DataRequired()])
    author = StringField('Author(s) (comma-separated)',
                         validators=[DataRequired()])
    genre = StringField('Genre', validators=[DataRequired()])
    year = IntegerField(
        'Year',
        validators=[
            DataRequired(message="Field 'Year' is required."),
            NumberRange(min=0, max=datetime.now().year,
                        message="Please enter a valid year (e.g. 1999).")
        ]
    )
    cover = FileField('Cover', validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], 'Only image files (jpg, png, jpeg) are allowed!')])
    submit = SubmitField('Submit', render_kw={"class": "btn"})


class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[
                                     DataRequired(), EqualTo('password')])
    submit = SubmitField('Add User', render_kw={"class": "btn"})


class UserEditForm(FlaskForm):
    username = StringField('Username', render_kw={'readonly': True})
    email = StringField('Email', validators=[DataRequired(), Email()])
    is_admin = BooleanField('Administrator privileges')
    submit = SubmitField('Save Changes')


class UserSettingsForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    picture = FileField('Update Profile Picture', validators=[
        FileAllowed(['jpg', 'png'], 'Images only!'),
        FileSize(max_size=2 * 1024 * 1024,
                 message='File size must be less than 2MB.')
    ])
    password = PasswordField('New Password', validators=[Optional()])
    confirm_password = PasswordField(
        'Confirm New Password',
        validators=[EqualTo('password', message='Passwords must match.')]
    )
    submit = SubmitField('Save Changes')


class LoanForm(FlaskForm):
    book_id = SelectField('Book', coerce=int, validators=[DataRequired()])
    user_id = SelectField('User', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Loan Book')
