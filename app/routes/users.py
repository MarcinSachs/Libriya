import os
import secrets
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from flask_babel import _

from app import db
from app.forms import UserForm, UserEditForm, UserSettingsForm
from app.models import User, Library
from app.utils import role_required
from app.utils.audit_log import (
    log_user_created, log_user_deleted, log_user_role_changed
)
from app.utils.messages import (
    USER_ADDED, USER_UPDATED, USER_DELETED, USER_CANNOT_DELETE_SELF,
    USER_CANNOT_DELETE_ADMIN, USER_NO_PERMISSION_EDIT, USER_NOT_IN_LIBRARY,
    USERS_NO_LIBRARY_MANAGED, USERS_NO_PERMISSION_EDIT_ROLE, USERS_ONLY_EDIT_OWN_LIBRARIES,
    USERS_CANNOT_REVOKE_LAST_ADMIN, USERS_NO_PERMISSION_CREATE_ADMIN, USERS_ONLY_DELETE_OWN_LIBRARIES,
    USERS_SETTINGS_NO_USER, USERS_SETTINGS_UPDATED, ERROR_PERMISSION_DENIED
)

bp = Blueprint("users", __name__)


@bp.route("/users/")
@login_required
@role_required('admin', 'manager')
def users():
    if current_user.role == 'admin':
        all_users = db.session.query(User).distinct().all()
    else:  # manager
        manager_library_ids = [lib.id for lib in current_user.libraries]
        if not manager_library_ids:
            # Show only self if not managing any library
            all_users = [current_user]
        else:
            all_users = db.session.query(User).join(User.libraries).filter(
                Library.id.in_(manager_library_ids)).distinct().all()

    return render_template("users.html", users=all_users, active_page="users", parent_page="admin")


@bp.route("/users/add/", methods=["GET", "POST"])
@login_required
@role_required('admin', 'manager')
def user_add():
    form = UserForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        # Create a new user and set their password
        user = User(username=username, email=email)
        user.set_password(password)

        # If manager is adding user, assign to manager's library
        if current_user.role == 'manager':
            if not current_user.libraries:
                flash(USERS_NO_LIBRARY_MANAGED, "danger")
                return render_template("user_add.html", form=form, parent_page="admin", active_page="users")
            # Add user to all libraries managed by this manager
            for library in current_user.libraries:
                user.libraries.append(library)

        # Add the user to the database
        db.session.add(user)
        db.session.commit()

        # Log user creation
        log_user_created(user.id, user.username, user.email)

        # Provide detailed success message
        if current_user.role == 'manager':
            library_names = ', '.join([lib.name for lib in current_user.libraries])
            flash(USER_ADDED % {'username': user.username}, "success")
        else:
            flash(USER_ADDED % {'username': user.username}, "success")
        return redirect(url_for("users.users"))
    return render_template("user_add.html", form=form, parent_page="admin", active_page="users")


@bp.route("/users/edit/<int:user_id>", methods=["GET", "POST"])
@login_required
@role_required('admin', 'manager')
def user_edit(user_id):
    user_to_edit = User.query.get_or_404(user_id)

    # --- Authorization Checks ---
    if current_user.role == 'manager':
        # Managers cannot edit admins or other managers unless editing themselves
        if user_to_edit.role in ['admin', 'manager'] and user_to_edit.id != current_user.id:
            flash(USERS_NO_PERMISSION_EDIT_ROLE, "danger")
            return redirect(url_for('users.users'))

        # Check if the user is in one of the manager's libraries (unless editing self)
        manager_libs_ids = {lib.id for lib in current_user.libraries}
        user_libs_ids = {lib.id for lib in user_to_edit.libraries}
        if not manager_libs_ids.intersection(user_libs_ids) and user_to_edit.id != current_user.id:
            flash(USERS_ONLY_EDIT_OWN_LIBRARIES, "danger")
            return redirect(url_for('users.users'))

    form = UserEditForm(obj=user_to_edit)

    # Determine which libraries can be managed
    if current_user.role == 'admin':
        manageable_libraries = Library.query.order_by('name').all()
    else:  # manager
        manageable_libraries = current_user.libraries

    # A manager should not be able to elevate a user to admin
    if current_user.role == 'manager':
        form.role.choices = [
            ('user', 'User'),
            ('manager', 'Manager')
        ]

    if form.validate_on_submit():
        # Prevent the last admin from being demoted
        last_admin = (
            user_to_edit.role == 'admin' and
            form.role.data != 'admin' and
            User.query.filter_by(role='admin').count() <= 1
        )
        if last_admin:
            flash(USERS_CANNOT_REVOKE_LAST_ADMIN, "danger")
            return redirect(url_for('users.user_edit',
                                    user_id=user_to_edit.id))

        # Prevent a manager from making someone an admin
        if current_user.role == 'manager' and form.role.data == 'admin':
            flash(USERS_NO_PERMISSION_CREATE_ADMIN, "danger")
            return redirect(url_for('users.user_edit',
                                    user_id=user_to_edit.id))

        # Track role changes for audit log
        old_role = user_to_edit.role
        user_to_edit.email = form.email.data
        user_to_edit.role = form.role.data

        # Log role change if it occurred
        if old_role != user_to_edit.role:
            log_user_role_changed(user_to_edit.id, user_to_edit.username, old_role, user_to_edit.role)

        # --- Update Library Memberships ---
        submitted_ids = {int(id) for id in request.form.getlist('libraries')}
        manageable_ids = {lib.id for lib in manageable_libraries}

        # Add new memberships
        for lib_id in submitted_ids:
            if lib_id in manageable_ids:
                library = Library.query.get(lib_id)
                if library not in user_to_edit.libraries:
                    user_to_edit.libraries.append(library)

        # Remove old memberships
        for lib_id in manageable_ids:
            if lib_id not in submitted_ids:
                library = Library.query.get(lib_id)
                if library in user_to_edit.libraries:
                    user_to_edit.libraries.remove(library)

        db.session.commit()
        flash(USER_UPDATED % {'username': user_to_edit.username}, "success")
        return redirect(url_for("users.users"))

    return render_template(
        "user_edit.html",
        form=form,
        user=user_to_edit,
        all_libraries=manageable_libraries,
        parent_page="admin",
        active_page="users",
        title=_("Edit User: %(username)s", username=user_to_edit.username)
    )


@bp.route("/users/delete/<int:user_id>", methods=['POST'])
@login_required
@role_required('admin', 'manager')
def user_delete(user_id):
    user_to_delete = User.query.get_or_404(user_id)

    # --- Authorization Checks ---
    # Cannot delete yourself
    if user_to_delete.id == current_user.id:
        flash(USER_CANNOT_DELETE_SELF, "danger")
        return redirect(url_for('users.users'))

    # Cannot delete admin users
    if user_to_delete.role == 'admin':
        flash(USER_CANNOT_DELETE_ADMIN, "danger")
        return redirect(url_for('users.users'))

    if current_user.role == 'manager':
        # Manager can only delete users in their libraries
        manager_libs_ids = {lib.id for lib in current_user.libraries}
        user_libs_ids = {lib.id for lib in user_to_delete.libraries}
        if not manager_libs_ids.intersection(user_libs_ids):
            flash(USERS_ONLY_DELETE_OWN_LIBRARIES, "danger")
            return redirect(url_for('users.users'))

    username = user_to_delete.username
    db.session.delete(user_to_delete)
    db.session.commit()

    # Log user deletion
    log_user_deleted(user_to_delete.id, username)

    flash(USER_DELETED % {'username': username}, "success")
    return redirect(url_for('users.users'))


@bp.route("/user/profile/<int:user_id>")
@login_required
def user_profile(user_id):
    user = current_user
    # Sort all loans by date, newest first
    all_loans = sorted(
        user.loans, key=lambda x: x.reservation_date, reverse=True)
    active_loans = [loan for loan in all_loans if loan.status == 'active']
    loan_history = [
        loan for loan in all_loans
        if loan.status == 'returned' or loan.status == 'cancelled'
    ]
    pending_loans = [loan for loan in all_loans if loan.status == 'pending']

    # Access favorites
    favorite_books = user.favorites

    return render_template(
        "user_profile.html",
        user=user,
        loans=all_loans,
        active_loans=active_loans,
        loan_history=loan_history,
        pending_loans=pending_loans,
        favorite_books=favorite_books,
        title=f"{user.username}"
    )


@bp.route("/user/settings", methods=["GET", "POST"])
@login_required
def user_settings():
    from flask_babel import _
    user = current_user
    if not user:
        flash(USERS_SETTINGS_NO_USER, "danger")
        return redirect(url_for('main.home'))

    form = UserSettingsForm(obj=user)

    if form.validate_on_submit():
        if form.picture.data:
            # Create a secure, unique filename
            random_hex = secrets.token_hex(8)
            _, f_ext = os.path.splitext(form.picture.data.filename)
            picture_filename = random_hex + f_ext
            picture_path = os.path.join(
                current_app.config["UPLOAD_FOLDER"], picture_filename)
            form.picture.data.save(picture_path)
            user.image_file = picture_filename

        user.email = form.email.data
        if form.password.data:
            user.set_password(form.password.data)
            # Log password change
            from app.utils.audit_log import log_password_changed
            log_password_changed(user.id, user.username)
        db.session.commit()
        flash(USERS_SETTINGS_UPDATED, "success")
        return redirect(url_for('users.user_profile', user_id=user.id))

    image_file_url = url_for(
        'static',
        filename='uploads/' + user.image_file
    )
    return render_template(
        "user_settings.html",
        form=form,
        title="My Settings",
        image_file_url=image_file_url,
        user=user
    )
