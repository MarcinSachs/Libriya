from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from flask_babel import _

from app.models import User, InvitationCode, Tenant
from app import db, limiter
from app.forms import RegistrationForm
from app.utils.audit_log import log_invitation_code_used
from app.utils.messages import (
    AUTH_LOGIN_SUCCESS, AUTH_INVALID_CREDENTIALS, AUTH_LOGOUT_SUCCESS,
    AUTH_REGISTRATION_SUCCESS
)
from datetime import datetime

bp = Blueprint("auth", __name__)


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
    if user and user.check_password(password):
        login_user(user)
        
        # Super-admin (tenant_id=NULL) -> admin panel
        if user.is_super_admin:
            flash(AUTH_LOGIN_SUCCESS, 'success')
            return redirect(url_for('admin.dashboard'))
        
        # Tenant-admin/user -> redirect do subdomeny tenanta
        if tenant and tenant.subdomain:
            redirect_url = f"http://{tenant.subdomain}.{request.host}/dashboard"
            flash(AUTH_LOGIN_SUCCESS, 'success')
            return redirect(redirect_url)
        else:
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
            tenant_id=code.tenant_id,
            libraries=[code.library],
            role='user'  # lub na podstawie zaproszenia
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

    return render_template('auth/register.html', form=form)
