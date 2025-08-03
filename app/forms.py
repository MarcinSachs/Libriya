from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, PasswordField, SelectField
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import DataRequired, NumberRange, Email, EqualTo
from datetime import datetime


class BookForm(FlaskForm):
    isbn = StringField('ISBN')
    title = StringField('Title', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
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


class LoanForm(FlaskForm):
    book_id = SelectField('Book', coerce=int, validators=[DataRequired()])
    user_id = SelectField('User', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Loan Book')
