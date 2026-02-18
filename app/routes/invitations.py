import secrets
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from flask_babel import _
from datetime import datetime, timedelta

from app import db
from app.models import InvitationCode, Library
from app.utils import role_required
from app.utils.audit_log import (
    log_invitation_code_generated, log_invitation_code_deactivated
)
from app.utils.messages import (
    INVITATION_CODE_GENERATED, INVITATION_CODE_DEACTIVATED,
    INVITATIONS_SELECT_LIBRARY, INVITATIONS_ONLY_OWN_LIBRARIES,
    INVITATIONS_CODE_GENERATED, INVITATIONS_NO_PERMISSION_DEACTIVATE,
    INVITATIONS_CANNOT_DEACTIVATE_USED, INVITATIONS_CODE_DEACTIVATED
)

bp = Blueprint("invitations", __name__, url_prefix='/invitation-codes')


def generate_invitation_code():
    """Generate a unique 8-character invitation code"""
    while True:
        code = secrets.token_hex(4).upper()  # 8 characters
        if not InvitationCode.query.filter_by(code=code, tenant_id=current_user.tenant_id).first():
            return code


@bp.route('/')
@login_required
@role_required('admin', 'manager')
def invitation_codes_list():
    """List invitation codes (multi-tenant filter)"""
    if current_user.role == 'admin':
        codes = InvitationCode.query.filter_by(tenant_id=current_user.tenant_id).order_by(InvitationCode.created_at.desc()).all()
    else:  # manager - only for their libraries
        library_ids = [lib.id for lib in current_user.libraries]
        codes = InvitationCode.query.filter(
            InvitationCode.library_id.in_(library_ids),
            InvitationCode.tenant_id == current_user.tenant_id
        ).order_by(InvitationCode.created_at.desc()).all()

    return render_template('superadmin/invitation_codes.html', codes=codes, now=datetime.utcnow,
                           active_page='invitations', parent_page='admin')


@bp.route('/generate', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def generate_code():
    """Generate new invitation code"""
    if request.method == 'POST':
        library_id = request.form.get('library_id', type=int)
        days_valid = request.form.get('days_valid', 7, type=int)

        # Validate library selection
        if not library_id:
            flash(INVITATIONS_SELECT_LIBRARY, 'danger')
            if current_user.role == 'admin':
                libraries = Library.query.filter_by(tenant_id=current_user.tenant_id).all()
            else:
                libraries = [lib for lib in current_user.libraries if lib.tenant_id == current_user.tenant_id]
            return render_template('superadmin/generate_invitation.html', libraries=libraries)

        # Verify library access
        library = Library.query.filter_by(id=library_id, tenant_id=current_user.tenant_id).first_or_404()

        if current_user.role == 'manager':
            # Manager can only generate codes for their libraries
            if library_id not in [lib.id for lib in current_user.libraries]:
                flash(INVITATIONS_ONLY_OWN_LIBRARIES, 'danger')
                return redirect(url_for('invitations.invitation_codes_list'))

        # Generate code
        code = generate_invitation_code()
        expires_at = datetime.utcnow() + timedelta(days=days_valid)

        invitation = InvitationCode(
            code=code,
            created_by_id=current_user.id,
            library_id=library_id,
            expires_at=expires_at
        )

        db.session.add(invitation)
        db.session.commit()

        # Audit log
        log_invitation_code_generated(code, library.id, library.name, days_valid)

        flash(INVITATIONS_CODE_GENERATED % {'code': code}, 'success')
        return redirect(url_for('invitations.invitation_codes_list'))

    # GET request
    if current_user.role == 'admin':
        libraries = Library.query.filter_by(tenant_id=current_user.tenant_id).all()
    else:  # manager
        libraries = [lib for lib in current_user.libraries if lib.tenant_id == current_user.tenant_id]

    return render_template('superadmin/generate_invitation.html', libraries=libraries)


@bp.route('/<int:code_id>/deactivate', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def deactivate_code(code_id):
    """Deactivate an invitation code"""
    code = InvitationCode.query.filter_by(id=code_id, tenant_id=current_user.tenant_id).first_or_404()

    # Verify access
    if current_user.role == 'manager':
        if code.library_id not in [lib.id for lib in current_user.libraries]:
            flash(INVITATIONS_NO_PERMISSION_DEACTIVATE, 'danger')
            return redirect(url_for('invitations.invitation_codes_list'))

    # Can't deactivate already used codes
    if code.used_by_id is not None:
        flash(INVITATIONS_CANNOT_DEACTIVATE_USED, 'warning')
        return redirect(url_for('invitations.invitation_codes_list'))

    # Audit log
    log_invitation_code_deactivated(code.code, code.library.name)

    db.session.delete(code)
    db.session.commit()

    flash(INVITATIONS_CODE_DEACTIVATED, 'info')
    return redirect(url_for('invitations.invitation_codes_list'))


@bp.route('/<int:code_id>/copy', methods=['POST'])
@login_required
@role_required('admin', 'manager')
def copy_code(code_id):
    """API endpoint to get code for copying"""
    code = InvitationCode.query.filter_by(id=code_id, tenant_id=current_user.tenant_id).first_or_404()

    # Verify access
    if current_user.role == 'manager':
        if code.library_id not in [lib.id for lib in current_user.libraries]:
            return jsonify({'error': 'Unauthorized'}), 403

    return jsonify({'code': code.code})
