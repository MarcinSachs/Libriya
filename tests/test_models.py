from datetime import datetime, timedelta
import pytest

from app import db
from app.models import (
    User, Tenant, Library, Book, Genre, Loan, Comment, InvitationCode
)


def test_user_password_and_role_properties(app):
    u = User(username='u1', email='u1@example.com', role='user')
    u.set_password('s3cr3t')
    db.session.add(u)
    db.session.commit()

    assert u.check_password('s3cr3t')
    assert not u.check_password('wrong')
    assert not u.is_admin
    assert not u.is_manager
    assert not u.is_super_admin

    # super-admin
    sa = User(username='sa', email='sa@example.com', role='superadmin')
    sa.set_password('p')
    db.session.add(sa)
    db.session.commit()
    assert sa.is_super_admin

    # tenant admin (role=admin + tenant_id)
    t = Tenant(name='T1', subdomain='t1')
    db.session.add(t)
    db.session.commit()

    ta = User(username='ta', email='ta@example.com', role='admin', tenant_id=t.id)
    ta.set_password('p')
    db.session.add(ta)
    db.session.commit()
    assert ta.is_tenant_admin


def test_tenant_premium_features_and_str(app):
    t = Tenant(name='PremiumTenant', subdomain='pt')
    t.premium_bookcover_enabled = True
    db.session.add(t)
    db.session.commit()

    assert 'bookcover_api' in t.get_enabled_premium_features()
    assert t.is_premium_enabled('bookcover_api')
    assert not t.is_premium_enabled('biblioteka_narodowa')
    assert str(t).startswith('PremiumTenant')


def test_library_defaults_and_relationships(app):
    tenant = Tenant(name='LT', subdomain='lt')
    db.session.add(tenant)
    db.session.commit()

    lib = Library(name='LibX', tenant_id=tenant.id)
    db.session.add(lib)
    db.session.commit()

    # default loan_overdue_days should be present
    assert lib.loan_overdue_days == 14

    # books relationship/backref
    g = Genre(name='G')
    db.session.add(g)
    db.session.commit()

    book = Book(title='B1', library_id=lib.id, tenant_id=tenant.id, year=2020)
    book.genres.append(g)
    db.session.add(book)
    db.session.commit()

    assert book in lib.books
    assert lib == book.library
    assert g in book.genres


def test_loan_and_comment_for_tenant_and_str(app):
    tenant = Tenant(name='LoanTenant', subdomain='lt2')
    db.session.add(tenant)
    db.session.commit()

    lib = Library(name='LoanLib', tenant_id=tenant.id)
    db.session.add(lib)
    db.session.commit()

    user = User(username='lu', email='lu@example.com', role='user', tenant_id=tenant.id)
    user.set_password('p')
    db.session.add(user)
    db.session.commit()

    book = Book(title='LoanBook', library_id=lib.id, tenant_id=tenant.id, year=2021)
    db.session.add(book)
    db.session.commit()

    loan = Loan(book_id=book.id, user_id=user.id, tenant_id=tenant.id)
    db.session.add(loan)
    db.session.commit()

    # Loan.for_tenant should return the loan
    loans = Loan.for_tenant(tenant.id).all()
    assert any(l.id == loan.id for l in loans)
    assert str(loan).startswith('Loan')

    # Comment.for_tenant uses Book.tenant_id in join
    comment = Comment(text='Nice', user_id=user.id, book_id=book.id, tenant_id=tenant.id)
    db.session.add(comment)
    db.session.commit()

    comments = Comment.for_tenant(tenant.id).all()
    assert any(c.id == comment.id for c in comments)


def test_invitation_code_validity_and_mark_used(app):
    tenant = Tenant(name='InvTenant', subdomain='inv')
    db.session.add(tenant)
    db.session.commit()

    lib = Library(name='InvLib', tenant_id=tenant.id)
    db.session.add(lib)
    db.session.commit()

    creator = User(username='creator', email='c@example.com', role='admin', tenant_id=tenant.id)
    creator.set_password('p')
    db.session.add(creator)
    db.session.commit()

    future = datetime.utcnow() + timedelta(days=7)
    past = datetime.utcnow() - timedelta(days=1)

    code = InvitationCode(code='VALID123', created_by_id=creator.id, library_id=lib.id, tenant_id=tenant.id, expires_at=future)
    db.session.add(code)
    db.session.commit()

    assert code.is_valid()

    # expired
    code2 = InvitationCode(code='EXPR0001', created_by_id=creator.id, library_id=lib.id, tenant_id=tenant.id, expires_at=past)
    db.session.add(code2)
    db.session.commit()
    assert not code2.is_valid()

    # mark as used
    new_user = User(username='newu', email='new@example.com', role='user', tenant_id=tenant.id)
    new_user.set_password('p')
    db.session.add(new_user)
    db.session.commit()

    code.mark_as_used(new_user.id)
    assert code.used_by_id == new_user.id
    assert code.used_at is not None
    assert not code.is_valid()


def test_user_for_tenant_query(app):
    tenant = Tenant(name='Utenant', subdomain='ut')
    db.session.add(tenant)
    db.session.commit()

    u1 = User(username='u_a', email='a@u.com', tenant_id=tenant.id)
    u1.set_password('p')
    u2 = User(username='u_b', email='b@u.com', tenant_id=tenant.id)
    u2.set_password('p')
    db.session.add_all([u1, u2])
    db.session.commit()

    users = User.for_tenant(tenant.id).all()
    assert len(users) == 2
