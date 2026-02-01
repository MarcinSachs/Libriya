from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_babel import _

from app import db
from app.forms import LibraryForm
from app.models import Library
from app.utils import role_required
from app.utils.messages import (
    LIBRARY_ADDED, LIBRARY_UPDATED, LIBRARY_DELETED,
    LIBRARIES_CANNOT_DELETE_WITH_BOOKS, LIBRARIES_CANNOT_DELETE_WITH_USERS
)

bp = Blueprint("libraries", __name__)


@bp.route("/libraries/")
@login_required
@role_required('admin', 'manager')
def libraries():
    if current_user.is_admin:
        all_libraries = Library.query.order_by(Library.name).all()
    elif current_user.is_manager:
        all_libraries = current_user.libraries
    else:
        all_libraries = []
    return render_template("libraries.html", libraries=all_libraries, active_page="libraries", parent_page="admin", title=_("Libraries"))


@bp.route("/libraries/add", methods=['GET', 'POST'])
@login_required
@role_required('admin')
def library_add():
    form = LibraryForm()
    if form.validate_on_submit():
        new_library = Library(name=form.name.data, loan_overdue_days=form.loan_overdue_days.data)
        db.session.add(new_library)
        db.session.commit()
        flash(LIBRARY_ADDED, "success")
        return redirect(url_for('libraries.libraries'))
    return render_template('library_form.html', form=form, title=_('Add Library'), active_page="libraries", parent_page="admin")


@bp.route("/libraries/edit/<int:library_id>", methods=['GET', 'POST'])
@login_required
@role_required('admin', 'manager')
def library_edit(library_id):
    library = Library.query.get_or_404(library_id)
    # Manager może edytować tylko swoje biblioteki
    if current_user.is_manager and library not in current_user.libraries:
        flash(_('You do not have permission to edit this library.'), 'danger')
        return redirect(url_for('libraries.libraries'))
    form = LibraryForm(obj=library)
    if form.validate_on_submit():
        library.name = form.name.data
        library.loan_overdue_days = form.loan_overdue_days.data
        db.session.commit()
        flash(LIBRARY_UPDATED, "success")
        return redirect(url_for('libraries.libraries'))
    return render_template('library_form.html', form=form, title=_('Edit Library'), active_page="libraries", parent_page="admin")


@bp.route("/libraries/delete/<int:library_id>", methods=['POST'])
@login_required
@role_required('admin')
def library_delete(library_id):
    library = Library.query.get_or_404(library_id)
    if library.books:
        flash(LIBRARIES_CANNOT_DELETE_WITH_BOOKS, "danger")
        return redirect(url_for('libraries.libraries'))
    # Also check if users are assigned to this library
    if library.users:
        flash(LIBRARIES_CANNOT_DELETE_WITH_USERS, "danger")
        return redirect(url_for('libraries.libraries'))
    db.session.delete(library)
    db.session.commit()
    flash(LIBRARY_DELETED, "success")
    return redirect(url_for('libraries.libraries'))
