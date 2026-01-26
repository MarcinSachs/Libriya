from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user
from flask_babel import _

from app.models import User

bp = Blueprint("auth", __name__)


@bp.route("/login/")
def login():
    from flask_login import current_user
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    return render_template("login.html", login_page=True, title='Log In')


@bp.route("/login/", methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user)
        flash(_('Login successful!'), 'success')
        return redirect(url_for('main.home'))
    else:
        flash(_('Invalid username or password. Please try again.'), 'danger')
        return redirect(url_for('auth.login'))


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash(_('You have been logged out.'), 'info')
    return redirect(url_for('auth.login'))
