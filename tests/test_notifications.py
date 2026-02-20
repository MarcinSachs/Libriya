from datetime import datetime, timedelta
import pytest

from app import db
from app.models import Notification, User, Tenant, Library
from app.utils.notifications import create_notification


def test_create_notification_single_and_multiple(app):
    u1 = User(username='r1', email='r1@example.com')
    u1.set_password('password')
    u2 = User(username='r2', email='r2@example.com')
    u2.set_password('password')
    sender = User(username='sender', email='s@example.com')
    sender.set_password('password')
    db.session.add_all([u1, u2, sender])
    db.session.commit()

    # single recipient
    create_notification(u1, sender, 'Hello single', 'info')
    n = Notification.query.filter_by(recipient_id=u1.id).first()
    assert n is not None
    assert n.message == 'Hello single'
    assert n.sender_id == sender.id

    # multiple recipients
    create_notification([u1, u2], sender, 'Hello all', 'info')
    assert Notification.query.filter_by(message='Hello all').count() == 2


def login(client, username, password='password'):
    return client.post('/auth/login/', data={'email_or_username': username, 'password': password}, follow_redirects=True)


def test_view_and_mark_notification_as_read_routes(app, client):
    # prepare a user and notifications
    user = User(username='notif_user', email='nu@example.com')
    user.is_email_verified = True
    user.set_password('password')
    db.session.add(user)
    db.session.commit()

    n1 = Notification(recipient_id=user.id, sender_id=None, message='Notify 1', type='info', is_read=False)
    n2 = Notification(recipient_id=user.id, sender_id=None, message='Notify 2', type='info', is_read=False)
    db.session.add_all([n1, n2])
    db.session.commit()

    # login and view notifications
    resp = login(client, user.email)
    assert resp.status_code == 200

    # ensure client is authenticated (debug endpoint)
    dbg = client.get('/auth/debug-login')
    assert b'"is_authenticated": true' in dbg.data

    res = client.get('/notifications/')
    assert res.status_code == 200
    # page should include notification messages
    assert b'Notify 1' in res.data and b'Notify 2' in res.data

    # mark single notification as read
    post = client.post(f'/notifications/mark_read/{n1.id}', follow_redirects=True)
    assert post.status_code == 200

    n1_db = Notification.query.get(n1.id)
    assert n1_db.is_read

    # mark all as read
    post_all = client.post('/notifications/mark_all_read/', follow_redirects=True)
    assert post_all.status_code == 200

    n2_db = Notification.query.get(n2.id)
    assert n2_db.is_read


def test_non_owner_cannot_mark_read_unless_admin(app, client):
    # recipient owner
    owner = User(username='owner', email='owner@example.com')
    owner.is_email_verified = True
    owner.set_password('password')
    other = User(username='other', email='other@example.com')
    other.is_email_verified = True
    other.set_password('password')
    admin = User(username='adm', email='adm@example.com', role='admin')
    admin.is_email_verified = True
    admin.set_password('password')
    db.session.add_all([owner, other, admin])
    db.session.commit()

    notif = Notification(recipient_id=owner.id, sender_id=None, message='Owner only', type='info', is_read=False)
    db.session.add(notif)
    db.session.commit()

    # other user tries to mark owner's notification
    login(client, other.email)
    dbg_other = client.get('/auth/debug-login')
    assert b'"is_authenticated": true' in dbg_other.data

    resp = client.post(f'/notifications/mark_read/{notif.id}', follow_redirects=True)
    assert resp.status_code == 200
    # should not have been marked read
    assert not Notification.query.get(notif.id).is_read

    # admin can mark it as read
    login(client, admin.email)
    dbg_admin = client.get('/auth/debug-login')
    assert b'"is_authenticated": true' in dbg_admin.data
    resp2 = client.post(f'/notifications/mark_read/{notif.id}', follow_redirects=True)
    assert resp2.status_code == 200
    assert Notification.query.get(notif.id).is_read
