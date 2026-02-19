import pytest
from app.models import User, PasswordResetToken
from app import db
from unittest import mock


def test_rate_limit(client):
    # 3 allowed per hour, the 4th should be rate limited
    for i in range(3):
        res = client.post('/auth/password-reset', data={'email_or_username': 'nonexistent', 'csrf_token': ''})
        assert res.status_code in (302, 200)

    res = client.post('/auth/password-reset', data={'email_or_username': 'nonexistent', 'csrf_token': ''})
    # Flask-Limiter returns 429 on rate limit
    assert res.status_code == 429


def test_token_generation_and_email_sent(app, client, regular_user, monkeypatch):
    sent = {}

    def fake_send(user, reset_url):
        sent['user'] = user.email
        sent['url'] = reset_url
        return True

    # Patch the name imported into the auth route module
    monkeypatch.setattr('app.routes.auth.send_password_reset_email', fake_send)

    res = client.post('/auth/password-reset', data={'email_or_username': regular_user.email, 'csrf_token': ''})
    assert res.status_code in (302, 200)

    # There should be a token in DB for this user
    entry = PasswordResetToken.query.filter_by(user_id=regular_user.id).first()
    assert entry is not None
    assert 'url' in sent
    assert regular_user.email == sent['user']


def test_token_consume_changes_password_and_logs(app, client, regular_user):
    # Generate token manually
    token = PasswordResetToken.generate_token(regular_user.id, expires_in=3600)

    # Now post to confirm
    res = client.post('/auth/password-reset/confirm', data={'token': token, 'password': 'newpass', 'csrf_token': ''})
    assert res.status_code in (302, 200)

    # Reload user and check password
    u = User.query.get(regular_user.id)
    assert u.check_password('newpass')

    # Token should be marked used
    entry = PasswordResetToken.query.filter_by(user_id=regular_user.id).first()
    assert entry.used
