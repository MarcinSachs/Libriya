from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_babel import _
from sqlalchemy import or_

from app import db, csrf
from app.forms import LoanForm
from app.models import Book, Loan, User, Library, Notification
from app.utils import role_required, create_notification
from app.utils.audit_log import log_action
from app.utils.messages import (
    LOAN_CREATED, LOAN_UPDATED, LOAN_COMPLETED, BOOK_RESERVED,
    BOOK_ALREADY_RESERVED, ERROR_PERMISSION_DENIED,
    LOAN_FILTER_INVALID_USER, LOANS_BOOK_RESERVED, LOANS_BOOK_ALREADY_RESERVED,
    LOANS_BOOK_ON_LOAN, LOANS_BORROWED_SUCCESS, LOANS_BOOK_NOT_AVAILABLE,
    LOANS_RETURNED_SUCCESS, LOANS_BOOK_NOT_ON_LOAN, LOANS_APPROVED,
    LOANS_CANNOT_APPROVE_STATUS, LOANS_NOT_PENDING, LOANS_RESERVATION_CANCELLED,
    LOANS_CANCEL_NOT_PENDING, LOANS_ADMIN_RETURNED, LOANS_NOT_ACTIVE,
    LOANS_ADDED_SUCCESS, LOANS_BOOK_UNAVAILABLE, LOANS_INVALID_BOOK_USER,
    LOANS_CAN_ONLY_CANCEL_OWN, LOANS_USER_RESERVATION_CANCELLED, LOANS_CANNOT_CANCEL_NOT_PENDING
)

bp = Blueprint("loans", __name__)


@bp.route("/loans/")
@login_required
@role_required('admin', 'manager')
def loans():
    loan_query = Loan.for_tenant(current_user.tenant_id).join(Book).join(User)

    # --- LIBRARY BASED FILTERING FOR MANAGERS ---
    if current_user.role == 'manager':
        manager_lib_ids = [lib.id for lib in current_user.libraries if lib.tenant_id == current_user.tenant_id]
        if not manager_lib_ids:
            # If manager has no libraries, show no loans
            loan_query = loan_query.filter(Book.id == -1)
        else:
            loan_query = loan_query.filter(
                Book.library_id.in_(manager_lib_ids))
    # --- END OF FILTERING ---

    # Apply user filter
    user_filter_id = request.args.get('user')
    if user_filter_id:
        try:
            user_filter_id = int(user_filter_id)
            loan_query = loan_query.filter(Loan.user_id == user_filter_id)
        except ValueError:
            # Handle case where user_filter_id is not a valid integer
            flash(LOAN_FILTER_INVALID_USER, "danger")
     # Apply status filter
    status_filter = request.args.get('status')
    if status_filter:
        loan_query = loan_query.filter(Loan.status == status_filter)

    # Order the results for consistent display (e.g., by loan date descending)
    loan_query = loan_query.order_by(Loan.reservation_date.desc())

    # Execute the final query to get filtered loans
    filtered_loans = loan_query.all()

    # Get users for the user filter dropdown
    if current_user.role == 'admin':
        all_users = User.query.order_by(User.username).all()
    else:  # manager
        manager_lib_ids = [lib.id for lib in current_user.libraries]
        if not manager_lib_ids:
            all_users = []
        else:
            all_users = db.session.query(User).join(User.libraries).filter(
                Library.id.in_(manager_lib_ids)).order_by(User.username).distinct().all()

    unread_notifications_count = Notification.query.filter_by(
        recipient=current_user, is_read=False
    ).count()

    return render_template("loans/loans.html", loans=filtered_loans, users=all_users, active_page="loans", parent_page="admin", title=_("Loans"),
                           now=datetime.utcnow())


@bp.route("/request_reservation/<int:book_id>/<int:user_id>", methods=["GET", "POST"])
@login_required
def request_reservation(book_id, user_id):
    book = Book.query.get_or_404(book_id)
    user = User.query.get_or_404(user_id)

    # Check if book is avaible
    if book.status == 'available':
        # Check if user do not have reservation
        existing_loan = Loan.query.filter_by(
            book_id=book.id, user_id=user.id
        ).filter(or_(Loan.status == 'pending', Loan.status == 'active')).first()

        if existing_loan:
            flash(
                _("You already have an active or pending reservation for this book."), "info")
            return redirect(url_for("main.home"))

        # Change status to 'reserved'
        book.status = 'reserved'
        # Create new record with pending status
        new_loan = Loan(book=book, user=user,
                        reservation_date=datetime.utcnow(), status='pending', tenant_id=book.tenant_id)

        db.session.add(new_loan)
        db.session.commit()

        # --- Notifications for admins ---
        admins = User.query.filter_by(role='admin').all()
        message = _("%(username)s has requested to reserve \"%(title)s\".",
                    username=user.username, title=book.title)
        create_notification(admins, current_user, message,
                            'reservation_request', loan=new_loan)

        # Audit: reservation requested
        try:
            log_action('LOAN_REQUESTED', f'User {user.username} requested reservation for book {book.title}',
                       subject=new_loan, additional_info={'book_id': book.id, 'user_id': user.id})
        except Exception:
            pass

        flash(LOANS_BOOK_RESERVED, "success")
    elif book.status == 'reserved':
        flash(LOANS_BOOK_ALREADY_RESERVED, "danger")
    elif book.status == 'on_loan':
        flash(LOANS_BOOK_ON_LOAN, "danger")
    return redirect(url_for("main.home"))


@bp.route("/borrow/<int:book_id>/<int:user_id>", methods=["GET", "POST"])
@login_required
def borrow_book(book_id, user_id):
    book = Book.query.get_or_404(book_id)
    user = User.query.get_or_404(user_id)

    if book.status == 'available':
        book.status = 'on_loan'
        new_loan = Loan(book=book, user=user, status='active', issue_date=datetime.utcnow(), tenant_id=book.tenant_id)
        # defensive assignments to ensure DB value is correct
        new_loan.status = 'active'
        new_loan.issue_date = new_loan.issue_date or datetime.utcnow()
        db.session.add(new_loan)
        db.session.commit()
        # Audit: book borrowed
        try:
            log_action('LOAN_BORROWED', f'Book {book.title} borrowed by {user.username}',
                       subject=new_loan, additional_info={'book_id': book.id, 'user_id': user.id})
        except Exception:
            pass
        flash(LOANS_BORROWED_SUCCESS, "success")
    else:
        flash(LOANS_BOOK_NOT_AVAILABLE, "danger")
    return redirect(url_for("main.home"))


@bp.route("/return_book/<int:book_id>", methods=["GET", "POST"])
@login_required
def return_book(book_id):
    loan = Loan.query.filter_by(book_id=book_id, status='active').first()
    if loan:
        loan.book.status = 'available'
        loan.return_date = datetime.utcnow()
        loan.status = 'returned'
        db.session.commit()
        # Audit: book returned
        try:
            log_action('LOAN_RETURNED', f'Book {loan.book.title} returned by {loan.user.username}',
                       subject=loan, additional_info={'loan_id': loan.id})
        except Exception:
            pass
        flash(LOANS_RETURNED_SUCCESS, "success")
    else:
        # ZMIANA KOMUNIKATU
        flash(LOANS_BOOK_NOT_ON_LOAN, "danger")
    return redirect(url_for("main.home"))


@bp.route('/loans/approve/<int:loan_id>', methods=['POST'])
@login_required
@csrf.exempt
@role_required('admin', 'manager')
def approve_loan(loan_id):
    loan = Loan.query.get_or_404(loan_id)

    if loan.status == 'pending':
        # Check if book is already in reserved status and was not cancelled
        if loan.book.status == 'reserved':
            loan.status = 'active'
            loan.issue_date = datetime.utcnow()
            loan.book.status = 'on_loan'
            db.session.commit()

            try:
                log_action('LOAN_APPROVED', f'Loan {loan.id} approved by {current_user.username}',
                           subject=loan, additional_info={'loan_id': loan.id})
            except Exception:
                pass

            # --- Create notification for users ---
            message = _(
                "Your reservation for \"%(title)s\" has been approved!", title=loan.book.title)
            create_notification(loan.user, current_user,
                                message, 'loan_approved', loan=loan)

            flash(LOANS_APPROVED % {'title': loan.book.title, 'username': loan.user.username}, 'success')
        else:
            flash(LOANS_CANNOT_APPROVE_STATUS, 'danger')
    else:
        flash(LOANS_NOT_PENDING, 'info')
    return redirect(url_for('loans.loans'))


@bp.route('/loans/cancel/<int:loan_id>', methods=['POST'])
@login_required
@csrf.exempt
@role_required('admin', 'manager')
def cancel_loan(loan_id):
    loan = Loan.query.get_or_404(loan_id)

    if loan.status == 'pending':
        # Return 'available' status if was reserved
        if loan.book.status == 'reserved':
            loan.book.status = 'available'
        loan.status = 'cancelled'
        db.session.commit()

        try:
            log_action('LOAN_CANCELLED', f'Loan {loan.id} cancelled by {current_user.username}',
                       subject=loan, additional_info={'loan_id': loan.id})
        except Exception:
            pass

        # --- Create notification for users ---
        message = _("Your reservation for \"%(title)s\" has been cancelled by an administrator.",
                    title=loan.book.title)
        create_notification(loan.user, current_user,
                            message, 'loan_cancelled', loan=loan)

        flash(LOANS_RESERVATION_CANCELLED % {'title': loan.book.title, 'username': loan.user.username}, 'info')
    else:
        flash(LOANS_CANCEL_NOT_PENDING, 'danger')
    return redirect(url_for('loans.loans'))


@bp.route('/loans/return/<int:loan_id>', methods=['POST'])
@login_required
@csrf.exempt
@role_required('admin', 'manager')
def return_loan(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    if loan.status == 'active':
        loan.book.status = 'available'
        loan.return_date = datetime.utcnow()
        loan.status = 'returned'
        db.session.commit()

        # --- Create notification for user ---
        message = _("The book \"%(title)s\" that you loaned has been marked as returned.",
                    title=loan.book.title)
        create_notification(loan.user, current_user,
                            message, 'loan_returned', loan=loan)

        try:
            log_action('LOAN_RETURNED_ADMIN', f'Loan {loan.id} returned by admin {current_user.username}', subject=loan, additional_info={
                       'loan_id': loan.id})
        except Exception:
            pass

        flash(LOANS_ADMIN_RETURNED % {'title': loan.book.title}, 'success')
    else:
        flash(LOANS_NOT_ACTIVE, 'info')
    return redirect(url_for('loans.loans'))


@bp.route("/loans/<user_id>")
@login_required
def user_loans(user_id):
    user_loans = User.query.get_or_404(user_id).loans
    user_loans = sorted(
        user_loans, key=lambda x: x.reservation_date, reverse=True)
    return render_template("loans/loans.html", loans=user_loans, active_page="", title="My Loans")


@bp.route("/loans/add/", methods=["GET", "POST"])
@login_required
@role_required('admin', 'manager')
def loan_add():
    form = LoanForm()
    # Populate choices for books and users
    # We only want to loan available books
    form.book_id.choices = [(b.id, b.title) for b in Book.query.filter_by(
        status='available').order_by(Book.title).all()]
    form.user_id.choices = [(u.id, u.username)
                            for u in User.query.order_by(User.username).all()]

    if form.validate_on_submit():
        book = Book.query.get(form.book_id.data)
        user = User.query.get(form.user_id.data)
        if book and user and book.status == 'available':
            book.status = 'on_loan'
            new_loan = Loan(book=book, user=user,
                            reservation_date=datetime.utcnow(),
                            issue_date=datetime.utcnow(),
                            status='active', tenant_id=book.tenant_id)
            db.session.add(new_loan)
            db.session.commit()

            try:
                log_action('LOAN_CREATED_ADMIN', f'Loan {new_loan.id} created by admin {current_user.username} for user {user.username}', subject=new_loan, additional_info={
                           'loan_id': new_loan.id})
            except Exception:
                pass

            # --- Create notification for user ---
            message = _("A loan for \"%(title)s\" has been directly issued to you by an administrator.",
                        title=book.title)
            create_notification(user, current_user, message,
                                'admin_issued_loan', loan=new_loan)

            flash(LOANS_ADDED_SUCCESS, "success")
            return redirect(url_for("loans.loans"))
        elif book and (book.status == 'on_loan' or book.status == 'reserved'):
            flash(LOANS_BOOK_UNAVAILABLE, "danger")
        else:
            flash(LOANS_INVALID_BOOK_USER, "danger")
    return render_template("loans/loan_add.html", form=form, active_page="loans", parent_page="admin", title="Add Loan")


@bp.route('/user/loans/cancel/<int:loan_id>', methods=['POST'])
@login_required
@csrf.exempt
def user_cancel_reservation(loan_id):
    loan = Loan.query.get_or_404(loan_id)

    if loan.user_id != current_user.id:
        flash(LOANS_CAN_ONLY_CANCEL_OWN, "danger")
        return redirect(url_for('users.user_profile', user_id=current_user.id))

    if loan.status == 'pending':
        if loan.book.status == 'reserved':
            loan.book.status = 'available'
        loan.status = 'cancelled'
        db.session.commit()

        try:
            log_action('LOAN_CANCELLED_USER', f'Loan {loan.id} cancelled by user {current_user.username}', subject=loan, additional_info={
                       'loan_id': loan.id})
        except Exception:
            pass

        # --- Create notyfication for admin ---
        admins = User.query.filter_by(role='admin').all()
        message = _("%(username)s has cancelled their reservation for \"%(title)s\".",
                    username=current_user.username, title=loan.book.title)
        create_notification(admins, current_user, message,
                            'user_cancelled_reservation', loan=loan)

        flash(LOANS_USER_RESERVATION_CANCELLED % {'title': loan.book.title}, 'success')
    else:
        flash(LOANS_CANNOT_CANCEL_NOT_PENDING, 'danger')

    return redirect(url_for('users.user_profile', user_id=current_user.id))


@bp.route("/admin/send_overdue_reminder/<int:loan_id>", methods=['POST'])
@login_required
@csrf.exempt
@role_required('admin', 'manager')
def send_overdue_reminder(loan_id):
    loan = Loan.query.get_or_404(loan_id)

    overdue_days = loan.book.library.loan_overdue_days if loan.book and loan.book.library else 14
    if loan.status == 'active' and loan.issue_date and (datetime.utcnow() - loan.issue_date).days > overdue_days:
        message = _("Reminder: Your loan for \"%(title)s\" is overdue. Please return it as soon as possible.",
                    title=loan.book.title)
        create_notification(loan.user, current_user, message,
                            'overdue_reminder', loan=loan)
        flash(_("Overdue reminder sent to %(username)s for book \"%(title)s\".",
                username=loan.user.username, title=loan.book.title), "success")
    else:
        flash(
            _("Cannot send overdue reminder. Loan is not active or not overdue."), "danger")

    return redirect(url_for('loans.loans'))
