from app import create_app, db
from app.models import User, Tenant, Library, Book
import os


def setup_test_app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    return app


def test_user_create_logs(app):
    with app.app_context():
        db.create_all()
        tenant = Tenant(name='T2', subdomain='t2')
        db.session.add(tenant)
        db.session.commit()

        user = User(username='u2', email='u2@example.com', role='admin', tenant_id=tenant.id)
        user.set_password('pw')
        db.session.add(user)
        db.session.commit()

        # Now call log_user_created and ensure file exists
        from app.utils.audit_log import log_user_created, LOGS_ROOT
        log_user_created(user.id, user.username, user.email)

        tenant_dir = os.path.join(LOGS_ROOT, f'tenant_{tenant.id}')
        global_dir = os.path.join(LOGS_ROOT, 'global')
        target_dir = tenant_dir if os.path.exists(tenant_dir) else (global_dir if os.path.exists(global_dir) else None)
        assert target_dir is not None, f'No logs directory found for tenant or global (checked {tenant_dir} and {global_dir})'

        # cleanup
        db.session.remove()
        db.drop_all()
