import pytest
from app import db
from app.models import User, Tenant, Library, InvitationCode


def login(client, username, password='password'):
    return client.post('/auth/login/', data={'email_or_username': username, 'password': password}, follow_redirects=True)


def test_generate_code_with_email_sends_mail(client, app, monkeypatch):
    # prepare tenant, library, and admin user
    t = Tenant(name='Tmail', subdomain='tm')
    db.session.add(t)
    db.session.commit()

    lib = Library(name='LibMail', tenant_id=t.id)
    db.session.add(lib)
    db.session.commit()

    admin = User(username='mailadmin', email='mail@ex.com', role='admin', tenant_id=t.id)
    admin.is_email_verified = True
    admin.set_password('password')
    # user default language is English; for this test use Polish
    admin.preferred_locale = 'pl'
    db.session.add(admin)
    db.session.commit()

    # login as admin
    login(client, admin.email)

    sent = {}

    def fake_send(to_address, subject, body):
        sent['to'] = to_address
        sent['subject'] = subject
        sent['body'] = body
        return True

    monkeypatch.setattr('app.utils.mailer.send_generic_email', fake_send)

    # post generate invitation with recipient email (send now default true)
    data = {
        'library_id': lib.id,
        'days_valid': 5,
        'recipient_email': 'recipient@example.com',
        'send_now': 'on'
    }
    resp = client.post('/invitation-codes/generate', data=data, follow_redirects=True)
    assert resp.status_code == 200

    # record created
    code = InvitationCode.query.filter_by(library_id=lib.id).first()
    assert code is not None
    assert code.recipient_email == 'recipient@example.com'

    # mail sent
    assert sent['to'] == 'recipient@example.com'
    assert code.code in sent['body']
    assert lib.name in sent['body']  # library name should appear in message
    # subject should be translated to Polish because admin.preferred_locale was pl
    assert 'Zaproszenie' in sent['subject']


def test_generate_code_invalid_email_shows_error(client, app):
    t = Tenant(name='Tinv', subdomain='ti')
    db.session.add(t)
    db.session.commit()

    lib = Library(name='LibInv', tenant_id=t.id)
    db.session.add(lib)
    db.session.commit()

    admin = User(username='invadmin', email='inv@ex.com', role='admin', tenant_id=t.id)
    admin.is_email_verified = True
    admin.set_password('password')
    db.session.add(admin)
    db.session.commit()

    login(client, admin.email)

    data = {
        'library_id': lib.id,
        'days_valid': 5,
        'recipient_email': 'not-an-email'
    }
    resp = client.post('/invitation-codes/generate', data=data, follow_redirects=True)
    assert resp.status_code == 200
    # invalid address should prevent creation
    assert InvitationCode.query.filter_by(library_id=lib.id).count() == 0


def test_send_email_via_route(client, app, monkeypatch):
    # prepare tenant, library, admin
    t = Tenant(name='Tsnd', subdomain='ts')
    db.session.add(t)
    db.session.commit()
    lib = Library(name='LibSnd', tenant_id=t.id)
    db.session.add(lib)
    db.session.commit()
    admin = User(username='sndadmin', email='snd@ex.com', role='admin', tenant_id=t.id)
    admin.is_email_verified = True
    admin.set_password('password')
    db.session.add(admin)
    db.session.commit()

    # create invitation code without email
    code = InvitationCode(code='ABC12345', created_by_id=admin.id,
                          library_id=lib.id, tenant_id=t.id,
                          expires_at=None)
    db.session.add(code)
    db.session.commit()

    login(client, admin.email)

    sent = {}

    def fake_send(to_address, subject, body):
        sent['to'] = to_address
        sent['subject'] = subject
        sent['body'] = body
        return True
    monkeypatch.setattr('app.utils.mailer.send_generic_email', fake_send)

    # send via route providing email
    resp = client.post(f'/invitation-codes/{code.id}/send', json={'email': 'late@user.com'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('success')
    assert data.get('email') == 'late@user.com'

    # record updated
    c2 = InvitationCode.query.get(code.id)
    assert c2.recipient_email == 'late@user.com'
    assert c2.email_sent_at is not None
    assert sent['to'] == 'late@user.com'

    # now send again without providing email (should reuse stored)
    sent.clear()
    resp2 = client.post(f'/invitation-codes/{code.id}/send', json={})
    assert resp2.status_code == 200
    data2 = resp2.get_json()
    assert data2.get('success')
    assert sent['to'] == 'late@user.com'

    # invalid email
    resp3 = client.post(f'/invitation-codes/{code.id}/send', json={'email': 'notvalid'})
    assert resp3.status_code == 400


def test_generate_code_with_email_but_no_send(client, app, monkeypatch):
    t = Tenant(name='Tnosend', subdomain='tn')
    db.session.add(t)
    db.session.commit()
    lib = Library(name='LibNo', tenant_id=t.id)
    db.session.add(lib)
    db.session.commit()
    admin = User(username='nosend', email='no@ex.com', role='admin', tenant_id=t.id)
    admin.is_email_verified = True
    admin.set_password('password')
    db.session.add(admin)
    db.session.commit()
    login(client, admin.email)
    sent = {}

    def fake_send(to_address, subject, body):
        sent['to'] = to_address
        return True
    monkeypatch.setattr('app.utils.mailer.send_generic_email', fake_send)

    data = {
        'library_id': lib.id,
        'days_valid': 5,
        'recipient_email': 'later@example.com'
        # do not set send_now
    }
    resp = client.post('/invitation-codes/generate', data=data, follow_redirects=True)
    assert resp.status_code == 200
    assert sent == {}
    code = InvitationCode.query.filter_by(library_id=lib.id).first()
    assert code.recipient_email == 'later@example.com'
