from app import create_app, db
from app.models import User, Tenant, AuditLogFile
import os
import json
from datetime import datetime, timedelta
from app.utils.audit_log import LOGS_ROOT


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


def test_admin_audit_preview_and_delete(client, app):
    """Super-admin can preview a real audit file and delete it (file + metadata removed)."""
    with app.app_context():
        # create super-admin user
        user = User(username='super_preview', email='super_preview@example.com', role='superadmin')
        user.set_password('pw')
        user.is_email_verified = True
        db.session.add(user)
        db.session.commit()

        # Ensure logs dir and create a test log file in the global dir
        global_dir = os.path.join(LOGS_ROOT, 'global')
        os.makedirs(global_dir, exist_ok=True)
        filepath = os.path.join(global_dir, 'audit_test_preview.log')
        with open(filepath, 'w', encoding='utf-8') as fh:
            fh.write('TEST_PREVIEW_LINE_1\nTEST_PREVIEW_LINE_2\n')

        # Create metadata row
        alf = AuditLogFile(filename=filepath, size=os.path.getsize(filepath))
        db.session.add(alf)
        db.session.commit()
        alf_id = alf.id

        # login
        client.post('/auth/login/', data={'email_or_username': 'super_preview', 'password': 'pw'})

        # preview should succeed and show contents
        res = client.get(f'/admin/audit-logs/{alf_id}/preview')
        assert res.status_code == 200
        assert 'TEST_PREVIEW_LINE_1' in res.get_data(as_text=True)

        # delete should remove file and DB row
        res2 = client.post(f'/admin/audit-logs/{alf_id}/delete', data={'csrf_token': ''})
        assert res2.status_code in (200, 302)
        assert not os.path.exists(filepath)
        assert AuditLogFile.query.get(alf_id) is None


def test_admin_audit_preview_missing_file_redirects(client, app):
    """Previewing a metadata entry for a missing file redirects with an error."""
    with app.app_context():
        user = User(username='super_missing', email='super_missing@example.com', role='superadmin')
        user.set_password('pw')
        user.is_email_verified = True
        db.session.add(user)
        db.session.commit()

        # metadata points to a non-existent file inside LOGS_ROOT
        fake_path = os.path.join(LOGS_ROOT, 'global', 'audit_nonexistent.log')
        alf = AuditLogFile(filename=fake_path, size=0)
        db.session.add(alf)
        db.session.commit()

        client.post('/auth/login/', data={'email_or_username': 'super_missing', 'password': 'pw'})
        res = client.get(f'/admin/audit-logs/{alf.id}/preview', follow_redirects=True)
        assert res.status_code == 200
        # audit list page is returned after redirect; template doesn't render flash messages
        assert 'Audit Logs' in res.get_data(as_text=True)


def test_admin_audit_retention_removes_old_files(client, app):
    """Retention endpoint removes files older than retention period (metadata row deleted)."""
    with app.app_context():
        user = User(username='super_ret', email='super_ret@example.com', role='superadmin')
        user.set_password('pw')
        user.is_email_verified = True
        db.session.add(user)
        db.session.commit()

        # create an old audit file under LOGS_ROOT/global
        global_dir = os.path.join(LOGS_ROOT, 'global')
        os.makedirs(global_dir, exist_ok=True)
        filepath = os.path.join(global_dir, 'audit_old_for_retention.log')
        with open(filepath, 'w', encoding='utf-8') as fh:
            fh.write('OLD_LOG_LINE\n')

        # create metadata with created_at older than retention cutoff
        old_date = datetime.utcnow() - timedelta(days=365)
        alf = AuditLogFile(filename=filepath, size=os.path.getsize(filepath), created_at=old_date)
        db.session.add(alf)
        db.session.commit()
        alf_id = alf.id

        client.post('/auth/login/', data={'email_or_username': 'super_ret', 'password': 'pw'})

        # ensure file exists before
        assert os.path.exists(filepath)
        res = client.post('/admin/audit-logs/retention/run', data={'csrf_token': ''}, follow_redirects=True)
        assert res.status_code == 200
        # retention should remove file + metadata
        assert not os.path.exists(filepath)
        assert AuditLogFile.query.get(alf_id) is None
        assert 'Audit Logs' in res.get_data(as_text=True)


def test_admin_audit_access_denied_for_regular_user(client, app, regular_user):
    """Regular (non-super) user must not access super-admin audit endpoints."""
    # mark fixture user as verified so login succeeds
    with app.app_context():
        regular_user.is_email_verified = True
        db.session.commit()

    # login as regular_user (fixture sets password 'password')
    client.post('/auth/login/', data={'email_or_username': regular_user.username, 'password': 'password'})

    # listing should redirect to main.home (regular authenticated user -> no super-admin access)
    res = client.get('/admin/audit-logs')
    assert res.status_code == 302
    # main.home is the dashboard for logged-in users
    assert res.headers['Location'].endswith('/dashboard')

    # retention run should also redirect / be forbidden
    res2 = client.post('/admin/audit-logs/retention/run', data={'csrf_token': ''})
    assert res2.status_code in (302, 403)


def test_audit_log_delete_outside_logs_not_allowed(client, app, tmp_path):
    """Attempt to delete a file outside LOGS_ROOT should be blocked and metadata preserved."""
    with app.app_context():
        user = User(username='super_outside', email='super_outside@example.com', role='superadmin')
        user.set_password('pw')
        user.is_email_verified = True
        db.session.add(user)
        db.session.commit()

        # create a temporary file outside LOGS_ROOT
        outside_file = tmp_path / 'outside.log'
        outside_file.write_text('outside')

        alf = AuditLogFile(filename=str(outside_file), size=os.path.getsize(str(outside_file)))
        db.session.add(alf)
        db.session.commit()
        alf_id = alf.id

        client.post('/auth/login/', data={'email_or_username': 'super_outside', 'password': 'pw'})
        res = client.post(f'/admin/audit-logs/{alf_id}/delete', data={'csrf_token': ''}, follow_redirects=True)
        assert res.status_code == 200
        # file and metadata remain
        assert os.path.exists(str(outside_file))
        assert AuditLogFile.query.get(alf_id) is not None
        # admin list is returned after redirect (flash not rendered by that template)
        assert 'Audit Logs' in res.get_data(as_text=True)
