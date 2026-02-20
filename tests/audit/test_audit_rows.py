from datetime import datetime, timedelta
import json

from app.utils.audit_log import log_action_db
from app.utils.scheduler import cleanup_old_audit_rows
from app import db
from app.models import AuditLog


def test_log_action_db_creates_row(app):
    # ensure DB is empty for this action
    AuditLog.query.filter_by(action='TEST_DB_WRITE').delete()
    db.session.commit()

    entry = log_action_db('TEST_DB_WRITE', 'testing db audit', additional_info={'foo': 'bar', 'password': 'secret'})
    assert entry is not None

    fetched = AuditLog.query.filter_by(action='TEST_DB_WRITE').order_by(AuditLog.timestamp.desc()).first()
    assert fetched is not None
    assert 'foo' in (json.loads(fetched.details) if fetched.details else {})
    # password should be masked
    details = json.loads(fetched.details)
    assert details.get('password') == '***'


def test_cleanup_old_audit_rows_respects_retention(app):
    retention = app.config.get('AUDIT_RETENTION_DAYS', 30)

    # create old and new entries
    old_ts = datetime.utcnow() - timedelta(days=retention + 2)
    old = AuditLog(action='OLD', timestamp=old_ts, details='old')
    recent = AuditLog(action='RECENT', timestamp=datetime.utcnow(), details='recent')

    db.session.add(old)
    db.session.add(recent)
    db.session.commit()

    # run cleanup
    cleanup_old_audit_rows(app)

    assert AuditLog.query.filter_by(action='OLD').first() is None
    assert AuditLog.query.filter_by(action='RECENT').first() is not None


def test_log_action_creates_db_row_via_log_action(app):
    from app.utils.audit_log import log_action

    # cleanup any previous test entries
    AuditLog.query.filter_by(action='TEST_FILE_DB').delete()
    db.session.commit()

    log_action('TEST_FILE_DB', 'file+db audit test', additional_info={'sample': 'value'})

    fetched = AuditLog.query.filter_by(action='TEST_FILE_DB').first()
    assert fetched is not None
    assert fetched.details and 'sample' in (json.loads(fetched.details) if fetched.details else {})
