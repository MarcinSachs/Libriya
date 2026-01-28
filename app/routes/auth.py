from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user
from flask_babel import _

from app.models import User, InvitationCode
from app import db, limiter
from app.forms import RegistrationForm
from app.utils.audit_log import log_invitation_code_used
from app.utils.messages import (
    AUTH_LOGIN_SUCCESS, AUTH_INVALID_CREDENTIALS, AUTH_LOGOUT_SUCCESS,
    AUTH_REGISTRATION_SUCCESS
)
from datetime import datetime

bp = Blueprint("auth", __name__)


@bp.route("/login/")
def login():
    from flask_login import current_user
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    return render_template("login.html", login_page=True, title='Log In')


@bp.route("/login/", methods=['POST'])
@limiter.limit("5 per minute")
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user)
        flash(AUTH_LOGIN_SUCCESS, 'success')
        return redirect(url_for('main.home'))
    else:
        flash(AUTH_INVALID_CREDENTIALS, 'danger')
        return redirect(url_for('auth.login'))


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash(AUTH_LOGOUT_SUCCESS, 'info')
    return redirect(url_for('auth.login'))


@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def register():
    from flask_login import current_user
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # Get invitation code
        code = InvitationCode.query.filter_by(code=form.invitation_code.data).first()

        # Create user
        user = User(
            username=form.username.data,
            email=form.email.data,
            library_id=code.library_id
        )
        user.set_password(form.password.data)
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data

        db.session.add(user)
        db.session.flush()  # Get user ID

        # Mark code as used
        code.mark_as_used(user.id)
        db.session.commit()

        # Audit log
        log_invitation_code_used(
            code.code,
            user.id,
            user.username,
            code.library.name
        )

        flash(AUTH_REGISTRATION_SUCCESS, 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html', form=form)
