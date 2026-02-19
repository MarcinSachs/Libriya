import os
import json
import tempfile
from datetime import datetime, timedelta
from app import create_app, db
from app.models import User, Tenant, Library, Book, InvitationCode, ContactMessage
from app.utils import audit_log
import logging


def setup_test_app():
    # Ensure the factory picks up the in-memory SQLite DB for tests
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    return app


def test_full_audit_sweep_creates_logs(tmp_path):
    app = setup_test_app()
    with app.app_context():
        db.create_all()

        # Create tenant and user
        tenant = Tenant(name='T1', subdomain='t1')
        db.session.add(tenant)
        db.session.commit()

        user = User(username='u1', email='u1@example.com', role='admin', tenant_id=tenant.id)
        user.set_password('password')
        db.session.add(user)
        db.session.commit()

        # Create a library
        lib = Library(name='Lib1', tenant_id=tenant.id)
        db.session.add(lib)
        db.session.commit()

        # Create a book
        book = Book(title='B1', library_id=lib.id, tenant_id=tenant.id, year=2020)
        db.session.add(book)
        db.session.commit()

        # Create invitation
        code = InvitationCode(code='ABCD1234', created_by_id=user.id, library_id=lib.id,
                              tenant_id=tenant.id, expires_at=datetime.utcnow()+timedelta(days=7))
        db.session.add(code)
        db.session.commit()

        # Send contact message
        cm = ContactMessage(user_id=user.id, library_id=lib.id, subject='Hi', message='Hello')
        db.session.add(cm)
        db.session.commit()

        # Ensure logs dir
        audit_log.ensure_logs_dir()

        # --- CLEANUP LOGS BEFORE TEST ---
        tenant_dir = os.path.join(audit_log.LOGS_ROOT, f'tenant_{tenant.id}')
        global_dir = os.path.join(audit_log.LOGS_ROOT, 'global')
        for d in [tenant_dir, global_dir]:
            if os.path.exists(d):
                for f in os.listdir(d):
                    if f.startswith('audit_'):
                        try:
                            os.remove(os.path.join(d, f))
                        except Exception:
                            pass

        # Trigger several audit actions
        from app.utils.audit_log import log_action, log_user_created, log_user_deleted
        log_action('TEST_ACTION', 'Testing full sweep', subject=user, additional_info={'foo': 'bar'})
        log_user_created(user.id, user.username, user.email)
        log_action('LIBRARY_CREATED', f'Library {lib.name} created', subject=lib)
        log_action('BOOK_CREATED', f'Book {book.title} created', subject=book)
        log_action('INVITATION_CREATED', f'Invitation {code.code} generated', subject=code)
        log_action('CONTACT_MESSAGE', f'Contact message {cm.id} created', subject=cm)

        # --- FLUSH ALL LOGGERS ---
        for handler in logging.root.handlers:
            try:
                handler.flush()
            except Exception:
                pass
        # Dodatkowo flush handlerów z audit_log jeśli są
        if hasattr(audit_log, 'logger'):
            for handler in getattr(audit_log.logger, 'handlers', []):
                try:
                    handler.flush()
                except Exception:
                    pass

        # Debug: pokaż ścieżki i pliki
        print('LOGS_ROOT:', audit_log.LOGS_ROOT)
        print('tenant_dir:', tenant_dir)
        print('global_dir:', global_dir)
        if os.path.exists(tenant_dir):
            print('tenant_dir files:', os.listdir(tenant_dir))
        if os.path.exists(global_dir):
            print('global_dir files:', os.listdir(global_dir))

        # Check that log files exist in tenant-specific dir or fallback to global
        target_dir = None
        if os.path.exists(tenant_dir):
            target_dir = tenant_dir
        elif os.path.exists(global_dir):
            target_dir = global_dir

        assert target_dir is not None, f'No logs directory found for tenant or global (checked {tenant_dir} and {global_dir})'

        # Zbierz pliki z obu katalogów
        files = []
        for d in [tenant_dir, global_dir]:
            if os.path.exists(d):
                files.extend([os.path.join(d, f) for f in os.listdir(d) if f.startswith('audit_')])
        assert files, 'No audit log files found after actions.'
        # Przeszukaj wszystkie pliki logów
        actions = []
        for logfile in files:
            with open(logfile, 'r', encoding='utf-8') as fh:
                lines = [json.loads(l) for l in fh.readlines() if l.strip()]
                actions.extend([l['action'] for l in lines])
        assert 'TEST_ACTION' in actions
        assert 'USER_CREATED' in actions
        assert 'BOOK_CREATED' in actions

        # Cleanup
        db.session.remove()
        db.drop_all()
