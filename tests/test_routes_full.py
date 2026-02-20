from datetime import datetime, timedelta
from app import db
from app.models import Tenant, Library, User, Book, Loan, Notification


def login(client, username, password='password'):
    return client.post('/auth/login/', data={'email_or_username': username, 'password': password}, follow_redirects=True)


def test_reservation_and_admin_approval_flow(app, client):
    # Setup tenant, library, admin and user and a book
    t = Tenant(name='FlowTenant', subdomain='ft')
    db.session.add(t)
    db.session.commit()

    lib = Library(name='FlowLib', tenant_id=t.id)
    db.session.add(lib)
    db.session.commit()

    admin = User(username='flow_admin', email='fa@example.com', role='admin', tenant_id=t.id)
    admin.is_email_verified = True
    admin.set_password('password')

    user = User(username='flow_user', email='fu@example.com', tenant_id=t.id)
    user.is_email_verified = True
    user.set_password('password')

    db.session.add_all([admin, user])
    db.session.commit()

    book = Book(title='FlowBook', library_id=lib.id, tenant_id=t.id, year=2020, status='available')
    db.session.add(book)
    db.session.commit()

    # User requests reservation
    login(client, user.email)
    res = client.get(f'/request_reservation/{book.id}/{user.id}', follow_redirects=True)
    assert res.status_code == 200

    # Book should be reserved and pending loan created
    b = Book.query.get(book.id)
    assert b.status == 'reserved'
    loan = Loan.query.filter_by(book_id=book.id, user_id=user.id).first()
    assert loan is not None and loan.status == 'pending'

    # Admin approves the loan
    login(client, admin.email)
    rv = client.post(f'/loans/approve/{loan.id}', data={'csrf_token': ''}, follow_redirects=True)
    assert rv.status_code == 200

    loan_db = Loan.query.get(loan.id)
    assert loan_db.status == 'active'
    assert loan_db.book.status == 'on_loan'

    # Notification should have been created for the user (loan_approved)
    noty = Notification.query.filter_by(recipient_id=user.id, type='loan_approved').first()
    assert noty is not None


def test_borrow_and_return_flow(app, client):
    t = Tenant(name='BorrowTenant', subdomain='bt')
    db.session.add(t)
    db.session.commit()

    lib = Library(name='BorrowLib', tenant_id=t.id)
    db.session.add(lib)
    db.session.commit()

    user = User(username='borrower', email='br@example.com', tenant_id=t.id)
    user.is_email_verified = True
    user.set_password('password')
    db.session.add(user)
    db.session.commit()

    book = Book(title='BorrowBook', library_id=lib.id, tenant_id=t.id, year=2018, status='available')
    db.session.add(book)
    db.session.commit()

    login(client, user.email)
    # Borrow
    resp = client.get(f'/borrow/{book.id}/{user.id}', follow_redirects=True)
    assert resp.status_code == 200
    b = Book.query.get(book.id)
    assert b.status == 'on_loan'
    loan = Loan.query.filter_by(book_id=book.id, user_id=user.id).first()
    assert loan is not None and loan.status == 'active'

    # Return by user
    resp2 = client.get(f'/return_book/{book.id}', follow_redirects=True)
    assert resp2.status_code == 200
    loan_db = Loan.query.get(loan.id)
    assert loan_db.status == 'returned'
    assert loan_db.book.status == 'available'


def test_user_cancel_reservation_and_admin_notified(app, client):
    t = Tenant(name='CancelTenant', subdomain='ct2')
    db.session.add(t)
    db.session.commit()

    lib = Library(name='CancelLib', tenant_id=t.id)
    db.session.add(lib)
    db.session.commit()

    admin = User(username='cancel_admin', email='ca2@example.com', role='admin', tenant_id=t.id)
    admin.is_email_verified = True
    admin.set_password('password')

    user = User(username='cancel_user', email='cu2@example.com', tenant_id=t.id)
    user.is_email_verified = True
    user.set_password('password')

    db.session.add_all([admin, user])
    db.session.commit()

    book = Book(title='CancelBook', library_id=lib.id, tenant_id=t.id, year=2015, status='available')
    db.session.add(book)
    db.session.commit()

    # user requests reservation
    login(client, user.email)
    client.get(f'/request_reservation/{book.id}/{user.id}', follow_redirects=True)
    loan = Loan.query.filter_by(book_id=book.id, user_id=user.id).first()
    assert loan is not None and loan.status == 'pending'

    # user cancels reservation
    resp = client.post(f'/user/loans/cancel/{loan.id}', follow_redirects=True)
    assert resp.status_code == 200
    loan_db = Loan.query.get(loan.id)
    assert loan_db.status == 'cancelled'

    # admin should have been notified of the cancellation
    notif = Notification.query.filter_by(type='user_cancelled_reservation').first()
    assert notif is not None


def test_admin_send_overdue_reminder(app, client):
    t = Tenant(name='OverdueTenant', subdomain='ot')
    db.session.add(t)
    db.session.commit()

    lib = Library(name='OverdueLib', tenant_id=t.id)
    db.session.add(lib)
    db.session.commit()

    admin = User(username='over_admin', email='oa@example.com', role='admin', tenant_id=t.id)
    admin.is_email_verified = True
    admin.set_password('password')

    user = User(username='over_user', email='ou@example.com', tenant_id=t.id)
    user.is_email_verified = True
    user.set_password('password')

    db.session.add_all([admin, user])
    db.session.commit()

    book = Book(title='OverdueBook', library_id=lib.id, tenant_id=t.id, year=2010, status='on_loan')
    db.session.add(book)
    db.session.commit()

    # create loan active and set issue_date far in past
    loan = Loan(book_id=book.id, user_id=user.id, status='active', tenant_id=t.id)
    loan.issue_date = datetime.utcnow() - timedelta(days=60)
    db.session.add(loan)
    db.session.commit()

    login(client, admin.email)
    resp = client.post(f'/admin/send_overdue_reminder/{loan.id}', follow_redirects=True)
    assert resp.status_code == 200

    # notification should be created for the user
    n = Notification.query.filter_by(recipient_id=user.id, type='overdue_reminder').first()
    assert n is not None
