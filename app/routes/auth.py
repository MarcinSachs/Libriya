from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from flask_babel import _

from app.models import User, InvitationCode, Tenant, PasswordResetToken
from app import db, limiter
from app.forms import RegistrationForm
from app.utils.audit_log import log_invitation_code_used, log_failed_login, log_action
from app.utils.messages import (
    AUTH_LOGIN_SUCCESS, AUTH_INVALID_CREDENTIALS, AUTH_LOGOUT_SUCCESS,
    AUTH_REGISTRATION_SUCCESS
)
from datetime import datetime
from app.utils.mailer import send_password_reset_email
import hashlib

bp = Blueprint("auth", __name__, url_prefix="/auth")


def get_tenant_from_request():
    """
    Dedukuj tenant z subdomeny
    Zwraca Tenant object lub None
    """
    host_parts = request.host.split(':')[0].split('.')

    # localhost lub bez subdomeny
    if len(host_parts) == 1 or host_parts[0] in ('localhost', 'www'):
        return None

    subdomain = host_parts[0]
    tenant = Tenant.query.filter_by(subdomain=subdomain).first()
    return tenant


@bp.route("/login/")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    # Pobierz tenant z subdomeny (jeśli istnieje)
    tenant = get_tenant_from_request()

    return render_template(
        "auth/login.html",
        login_page=True,
        title='Log In',
        tenant=tenant
    )


@bp.route("/login/", methods=['POST'])
@limiter.limit("5 per minute")
def login_post():
    email_or_username = request.form.get('email_or_username')
    password = request.form.get('password')

    # KROK 1: Dedukuj tenant z subdomeny
    tenant_from_url = get_tenant_from_request()

    user = None
    tenant = None

    # KROK 2: Szukaj użytkownika
    if '@' in email_or_username:
        # Szukaj po email
        if tenant_from_url:
            # Ze subdomeny - szukaj w konkretnym tenanie
            user = User.query.filter_by(
                email=email_or_username,
                tenant_id=tenant_from_url.id
            ).first()
            tenant = tenant_from_url
        else:
            # Bez subdomeny - szukaj wszędzie
            user = User.query.filter_by(email=email_or_username).first()

            if user:
                # Sprawdź czy email nie istnieje w wielu tenantach
                users_count = User.query.filter_by(
                    email=email_or_username
                ).count()

                if users_count > 1:
                    # Email w wielu tenantach - błąd!
                    flash(
                        _("This email exists in multiple libraries. "
                          "Please log in from your library's page."),
                        'danger'
                    )
                    return redirect(url_for('auth.login'))

                tenant = user.tenant
    else:
        # Szukaj po username
        if tenant_from_url:
            # Ze subdomeny - szukaj w konkretnym tenanie
            user = User.query.filter_by(
                username=email_or_username,
                tenant_id=tenant_from_url.id
            ).first()
            tenant = tenant_from_url
        else:
            # Bez subdomeny - szukaj wszędzie
            user = User.query.filter_by(username=email_or_username).first()

            if user:
                # Sprawdź czy username nie istnieje w wielu tenantach
                users_count = User.query.filter_by(
                    username=email_or_username
                ).count()

                if users_count > 1:
                    flash(
                        _("This username exists in multiple libraries. "
                          "Please log in from your library's page."),
                        'danger'
                    )
                    return redirect(url_for('auth.login'))

                tenant = user.tenant

    # KROK 3: Walidacja hasła
    if user:
        password_ok = user.check_password(password)
        if password_ok:
            login_user(user)

            try:
                log_action('USER_LOGIN', f'User {user.username} logged in', subject=user, additional_info={'user_id': user.id})
            except Exception:
                pass

            # Super-admin (role='superadmin') -> tenants management panel
            if user.is_super_admin:
                flash(AUTH_LOGIN_SUCCESS, 'success')
                return redirect(url_for('admin.tenants_list'))

            # Tenant-admin/user -> zawsze redirect do landing page
            flash(AUTH_LOGIN_SUCCESS, 'success')
            return redirect(url_for('main.landing'))
        else:
            flash(_('Invalid password. Please check and try again.'), 'danger')
            try:
                log_failed_login(email_or_username)
            except Exception:
                pass
            return redirect(url_for('auth.login'))
    else:
        flash(_('User not found. Please check your email or username.'), 'danger')
        return redirect(url_for('auth.login'))


@bp.route('/debug-login')
def debug_login():
    """Debug endpoint - sprawdzenie czy login działa"""
    from flask_login import current_user
    import json

    return json.dumps({
        'is_authenticated': current_user.is_authenticated,
        'user_id': current_user.get_id() if current_user.is_authenticated else None,
        'username': current_user.username if current_user.is_authenticated else None,
        'email': current_user.email if current_user.is_authenticated else None,
    })


@bp.route('/debug-users')
def debug_users():
    """Debug endpoint - listuj wszystkich userów w database"""
    import json
    users = User.query.all()
    data = []
    for u in users:
        data.append({
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'tenant_id': u.tenant_id,
            'password_hash_length': len(u.password_hash) if u.password_hash else 0,
            'password_hash_preview': u.password_hash[:20] if u.password_hash else 'NONE'
        })
    return json.dumps(data, indent=2)


@bp.route('/debug-test-password/<username>')
def debug_test_password(username):
    """Test password check for a specific user"""
    import json
    user = User.query.filter_by(username=username).first()
    if not user:
        return json.dumps({'error': 'User not found', 'username': username})

    # Test password check with a simple password
    test_password = 'test123456'
    result = user.check_password(test_password)

    return json.dumps({
        'username': user.username,
        'email': user.email,
        'password_hash_length': len(user.password_hash),
        'test_password': test_password,
        'check_result': result,
        'message': 'If check_result=False, password does not match. This is expected if user was created with a different password.'
    }, indent=2)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    try:
        log_action('USER_LOGOUT', f'User {current_user.username} logged out', subject=current_user, additional_info={'user_id': current_user.id})
    except Exception:
        pass
    flash(AUTH_LOGOUT_SUCCESS, 'info')
    return redirect(url_for('auth.login'))


@bp.route('/register-choice', methods=['GET'])
def register_choice():
    """
    Strona wyboru typu rejestracji:
    - Nowy klient
    - Dołączenie do istniejącej biblioteki poprzez kod zaproszenia
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    return render_template('auth/register_choice.html')


@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

    # Get registration mode from query parameter
    mode = request.args.get('mode', 'create')  # Default to 'create'

    # Validate mode parameter
    if mode not in ['create', 'join']:
        return redirect(url_for('auth.register_choice'))

    creating_new_tenant = mode == 'create'
    # Note: For join mode, tenant is determined from invitation code, not subdomain

    form = RegistrationForm()

    # Set the create_new_tenant flag for form validation
    if request.method == 'GET':
        form.create_new_tenant.data = 'true' if creating_new_tenant else 'false'

    if form.validate_on_submit():
        try:
            if creating_new_tenant:
                # Scenario 1: Creating new tenant on main domain
                if not form.tenant_name.data:
                    flash(_('Organization name is required when creating a new organization'), 'error')
                    return render_template('auth/register.html', form=form, creating_new_tenant=creating_new_tenant)

                # Create new tenant
                new_tenant = Tenant(
                    name=form.tenant_name.data,
                    subdomain=form.tenant_name.data.lower().replace(' ', '-')[:50]
                )
                db.session.add(new_tenant)
                db.session.flush()  # Get tenant ID

                # Create user as owner
                user = User(
                    username=form.username.data,
                    email=form.email.data,
                    tenant_id=new_tenant.id,
                    role='admin'  # Owner of this tenant
                )
                user.set_password(form.password.data)
                # Auto-fill first_name and last_name from username and tenant name
                user.first_name = form.username.data.capitalize()
                user.last_name = form.tenant_name.data if form.tenant_name.data else 'Admin'

                db.session.add(user)
                db.session.commit()

                flash(_('Organization created successfully! Welcome {}. You can now log in.').format(
                    form.username.data), 'success')

            else:
                # Scenario 2: Joining existing tenant on subdomain
                if not form.invitation_code.data:
                    flash(_('Invitation code is required when joining an organization'), 'error')
                    return render_template('auth/register.html', form=form, creating_new_tenant=creating_new_tenant)

                # Get invitation code
                code = InvitationCode.query.filter_by(code=form.invitation_code.data).first()
                if not code:
                    flash(_('Invalid invitation code'), 'error')
                    return render_template('auth/register.html', form=form, creating_new_tenant=creating_new_tenant)

                # Create user - tenant is determined from invitation code
                user = User(
                    username=form.username.data,
                    email=form.email.data,
                    tenant_id=code.tenant_id,
                    libraries=[code.library],
                    role='user'
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

                flash(_('Account created successfully! Welcome {} {}. You can now log in.').format(
                    form.first_name.data, form.last_name.data), 'success')

            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            flash(_('An error occurred during registration: {}').format(str(e)), 'error')
            return render_template('auth/register.html', form=form, creating_new_tenant=creating_new_tenant)

    return render_template('auth/register.html', form=form, creating_new_tenant=creating_new_tenant)


@bp.route('/password-reset', methods=['POST'])
@limiter.limit("3 per hour")
def password_reset():
    """Handle password reset requests (rate-limited).

    This endpoint accepts a POST with 'email_or_username' or 'email' and
    responds with a generic message to avoid leaking account existence.
    Generates a one-time token (DB-backed) and triggers the mailer (which is
    mockable in tests)."""
    email_or_username = request.form.get('email_or_username') or request.form.get('email')

    user = None
    if email_or_username:
        if '@' in email_or_username:
            user = User.query.filter_by(email=email_or_username).first()
        else:
            user = User.query.filter_by(username=email_or_username).first()

    # If user exists, create a DB-backed token and send email (do not leak)
    try:
        if user:
            token = PasswordResetToken.generate_token(user.id, expires_in=3600)
            try:
                # Build absolute reset URL
                reset_url = url_for('auth.password_reset_confirm', token=token, _external=True)
                send_password_reset_email(user, reset_url)
                # Audit that reset link was issued
                log_action('PASSWORD_RESET_SENT', f'Password reset link issued for user {user.username}', subject=user, additional_info={'user_id': user.id})
            except Exception:
                # Don't fail the whole request if mail sending fails
                pass

        # Always log the request (do not reveal existence)
        try:
            log_action('PASSWORD_RESET_REQUESTED', f'Password reset requested for {email_or_username}', subject=user if user else None, additional_info={'identifier': email_or_username, 'user_id': user.id if user else None})
        except Exception:
            pass

    except Exception:
        # Ensure we don't leak internal errors
        try:
            log_action('PASSWORD_RESET_REQUEST_ERROR', f'Error while handling password reset for {email_or_username}', additional_info={'identifier': email_or_username})
        except Exception:
            pass

    flash(_('If an account with that email/username exists, a password reset link has been sent.'), 'info')
    return redirect(url_for('auth.login'))


@bp.route('/password-reset/confirm', methods=['GET', 'POST'])
def password_reset_confirm():
    """Consume a password reset token and set a new password.

    GET: optional redirect to a frontend form (not required for tests).
    POST: accepts 'token' and 'password'."""
    if request.method == 'GET':
        # Provide a simple page or redirect to login with token in querystring
        token = request.args.get('token')
        return render_template('auth/password_reset_confirm.html', token=token)

    # POST
    token = request.form.get('token')
    new_password = request.form.get('password')

    if not token or not new_password:
        flash(_('Token and new password are required.'), 'danger')
        return redirect(url_for('auth.login'))

    entry = PasswordResetToken.verify_token(token)
    if not entry:
        flash(_('Invalid or expired token.'), 'danger')
        return redirect(url_for('auth.login'))

    # All good - update password and mark token used
    try:
        user = entry.user
        user.set_password(new_password)
        db.session.add(user)
        entry.mark_used()
        db.session.commit()

        try:
            log_action('PASSWORD_CHANGED', f'Password changed for user {user.username}', subject=user, additional_info={'user_id': user.id})
        except Exception:
            pass

        flash(_('Your password has been changed. You can now log in.'), 'success')
        return redirect(url_for('auth.login'))
    except Exception as e:
        db.session.rollback()
        flash(_('An error occurred while resetting password.'), 'danger')
        return redirect(url_for('auth.login'))
