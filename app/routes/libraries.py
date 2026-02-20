from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from flask_babel import _

import secrets
from datetime import datetime

from app import db, csrf
from app.forms import LibraryForm
from app.models import Library, SharedLink
from app.utils import role_required
from app.utils.messages import (
    LIBRARY_ADDED, LIBRARY_UPDATED, LIBRARY_DELETED,
    LIBRARIES_CANNOT_DELETE_WITH_BOOKS, LIBRARIES_CANNOT_DELETE_WITH_USERS
)
from app.utils.audit_log import log_library_operation, log_action

bp = Blueprint("libraries", __name__)


@bp.route("/libraries/")
@login_required
@role_required('admin', 'manager')
def libraries():
    # eager-load shared links so template can show existing share info
    if current_user.is_admin:
        all_libraries = Library.query.options(db.subqueryload(Library.shared_links))
        all_libraries = all_libraries.filter_by(tenant_id=current_user.tenant_id).order_by(Library.name).all()
    elif current_user.is_manager:
        # limit to manager's libraries, load links manually
        libs = [lib for lib in current_user.libraries if lib.tenant_id == current_user.tenant_id]
        # ensure links are loaded (iterate without assigning to _)
        for l in libs:
            _unused = l.shared_links
        all_libraries = libs
    else:
        all_libraries = []
    return render_template("libraries/libraries.html", libraries=all_libraries, active_page="libraries", parent_page="admin", title=_("Libraries"))


@bp.route('/libraries/<int:library_id>/share', methods=['POST'])
@csrf.exempt
@login_required
@role_required('admin', 'manager')
def library_share(library_id):
    """Generate a share link for a library"""
    library = Library.query.filter_by(id=library_id, tenant_id=current_user.tenant_id).first_or_404()
    if current_user.role == 'manager' and library not in current_user.libraries:
        return jsonify({'error': _('You do not have permission to share this library')}), 403

    expires_str = request.form.get('expires_at', '').strip()
    expires_at = None
    if expires_str:
        try:
            expires_at = datetime.strptime(expires_str, '%Y-%m-%d')
        except Exception:
            return jsonify({'error': _('Invalid expiration date format')}), 400

    token = secrets.token_urlsafe(16)
    link = SharedLink(
        token=token,
        library_id=library.id,
        created_by_id=current_user.id,
        expires_at=expires_at,
        active=True
    )
    db.session.add(link)
    db.session.commit()

    url = url_for('share.view', token=token, _external=True)
    return jsonify({'success': True, 'token': token, 'url': url})


@bp.route('/libraries/<int:library_id>/share/deactivate', methods=['POST'])
@csrf.exempt
@login_required
@role_required('admin', 'manager')
def library_share_deactivate(library_id):
    lib = Library.query.filter_by(id=library_id, tenant_id=current_user.tenant_id).first_or_404()
    if current_user.role == 'manager' and lib not in current_user.libraries:
        return jsonify({'error': _('You do not have permission')}), 403
    # find active link
    link = SharedLink.query.filter_by(library_id=lib.id, active=True).first()
    if not link:
        return jsonify({'error': _('No active share link')}), 400
    link.active = False
    db.session.commit()
    return jsonify({'success': True})


@bp.route("/libraries/add", methods=['GET', 'POST'])
@login_required
@role_required('admin')
def library_add():
    form = LibraryForm()
    tenant = current_user.tenant
    # Enforce limit for non-superadmin
    if not current_user.is_super_admin and not tenant.can_add_library():
        flash(_('Your organization has reached the maximum number of libraries allowed. Contact support to increase your limit.'), 'danger')
        return redirect(url_for('libraries.libraries'))

    if form.validate_on_submit():
        new_library = Library(name=form.name.data, loan_overdue_days=form.loan_overdue_days.data,
                              tenant_id=current_user.tenant_id)
        db.session.add(new_library)
        db.session.commit()
        # Audit
        try:
            log_library_operation('created', new_library.id, new_library.name,
                                  f'Library created by {current_user.username}')
        except Exception:
            pass
        flash(LIBRARY_ADDED, "success")
        return redirect(url_for('libraries.libraries'))
    return render_template('libraries/library_form.html', form=form, title=_('Add Library'), active_page="libraries", parent_page="admin")


@bp.route("/libraries/edit/<int:library_id>", methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def library_edit(library_id):
    library = Library.query.filter_by(id=library_id, tenant_id=current_user.tenant_id).first_or_404()
    # Manager może edytować tylko swoje biblioteki
    if current_user.is_manager and library not in current_user.libraries:
        flash(_('You do not have permission to edit this library.'), 'danger')
        return redirect(url_for('libraries.libraries'))
    form = LibraryForm(obj=library)
    if form.validate_on_submit():
        library.name = form.name.data
        library.loan_overdue_days = form.loan_overdue_days.data
        db.session.commit()
        # Audit
        try:
            log_library_operation('updated', library.id, library.name, f'Library updated by {current_user.username}')
        except Exception:
            pass
        flash(LIBRARY_UPDATED, "success")
        return redirect(url_for('libraries.libraries'))
    return render_template('libraries/library_form.html', form=form, title=_('Edit Library'), active_page="libraries", parent_page="admin")


@bp.route("/libraries/delete/<int:library_id>", methods=['POST'])
@login_required
@role_required('admin')
def library_delete(library_id):
    library = Library.query.filter_by(id=library_id, tenant_id=current_user.tenant_id).first_or_404()
    if library.books:
        flash(LIBRARIES_CANNOT_DELETE_WITH_BOOKS, "danger")
        return redirect(url_for('libraries.libraries'))
    # Also check if users are assigned to this library
    if library.users:
        flash(LIBRARIES_CANNOT_DELETE_WITH_USERS, "danger")
        return redirect(url_for('libraries.libraries'))
    # Audit before deletion
    try:
        log_library_operation('deleted', library.id, library.name, f'Library deleted by {current_user.username}')
    except Exception:
        pass
    db.session.delete(library)
    db.session.commit()
    flash(LIBRARY_DELETED, "success")
    return redirect(url_for('libraries.libraries'))
