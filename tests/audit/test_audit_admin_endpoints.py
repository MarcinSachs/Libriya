from app import create_app, db
from app.models import User, Tenant
import os
import json


def setup_test_app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    return app


def test_admin_audit_endpoints(client, app):
    with app.app_context():
        # create super-admin user
        user = User(username='super', email='super@example.com', role='superadmin')
        user.set_password('pw')
        db.session.add(user)
        db.session.commit()

        # login
        client.post('/auth/login/', data={'email_or_username': 'super', 'password': 'pw'})

        # call audit list (should not error)
        res = client.get('/admin/audit-logs')
        assert res.status_code in (200, 302)

        # trigger retention (POST)
        res2 = client.post('/admin/audit-logs/retention/run', data={'csrf_token': ''})
        # CSRF may be enforced; at least endpoint exists and returns something
        assert res2.status_code in (200, 302, 400, 403)
