import pytest
from app.models import User, EmailVerificationToken
from app import db


def test_generate_and_mark_used(app):
    user = User(username='ev_test', email='ev@test.com')
    user.set_password('password')
    db.session.add(user)
    db.session.commit()

    token = EmailVerificationToken.generate_token(user.id, expires_in=3600)
    assert token is not None

    entry = EmailVerificationToken.verify_token(token)
    assert entry is not None
    assert entry.user_id == user.id

    entry.mark_used()
    # after marking used, verify_token should return None
    assert EmailVerificationToken.verify_token(token) is None


def test_verify_endpoint_marks_user_verified(client, app):
    # create user
    user = User(username='ev_web', email='evweb@test.com')
    user.set_password('password')
    db.session.add(user)
    db.session.commit()

    token = EmailVerificationToken.generate_token(user.id, expires_in=3600)
    # GET the verify endpoint
    resp = client.get(f'/auth/verify-email?token={token}', follow_redirects=True)
    assert resp.status_code == 200

    # Reload user from DB
    u = User.query.get(user.id)
    assert u.is_email_verified is True


def test_send_verification_endpoint_triggers_mail(client, app, monkeypatch):
    sent = {}

    def fake_send(to_address, subject, body):
        sent['to'] = to_address
        sent['subject'] = subject
        sent['body'] = body
        return True

    monkeypatch.setattr('app.utils.mailer.send_generic_email', fake_send)

    user = User(username='ev_send', email='evsend@test.com')
    user.set_password('password')
    db.session.add(user)
    db.session.commit()

    resp = client.post('/auth/verify-email/send', data={'email': user.email}, follow_redirects=True)
    assert resp.status_code == 200
    assert sent.get('to') == user.email

    # token created in DB
    entry = EmailVerificationToken.query.filter_by(user_id=user.id).first()
    assert entry is not None


def test_expired_token_is_rejected(client, app):
    user = User(username='ev_exp', email='evexp@test.com')
    user.set_password('password')
    db.session.add(user)
    db.session.commit()

    token = EmailVerificationToken.generate_token(user.id, expires_in=1)
    # Force expire by updating expires_at to past
    entry = EmailVerificationToken.query.filter_by(user_id=user.id).first()
    entry.expires_at = entry.expires_at - __import__('datetime').timedelta(days=1)
    db.session.add(entry)
    db.session.commit()

    resp = client.get(f'/auth/verify-email?token={token}', follow_redirects=True)
    assert resp.status_code == 200

    u = User.query.get(user.id)
    assert u.is_email_verified is False


def test_registration_sends_verification(client, app, monkeypatch):
    sent = {}

    def fake_send(to_address, subject, body):
        sent['to'] = to_address
        return True

    monkeypatch.setattr('app.utils.mailer.send_generic_email', fake_send)

    # Simulate registration (create new tenant)
    data = {
        'tenant_name': 'TestTenant',
        'username': 'reg_ev',
        'email': 'regev@test.com',
        'password': 'password',
        'password_confirm': 'password',
        'create_new_tenant': 'true'
    }

    resp = client.post('/auth/register?mode=create', data=data, follow_redirects=True)
    assert resp.status_code == 200

    user = User.query.filter_by(username='reg_ev').first()
    assert user is not None
    # token should be created
    entry = EmailVerificationToken.query.filter_by(user_id=user.id).first()
    assert entry is not None
    assert sent.get('to') == user.email
