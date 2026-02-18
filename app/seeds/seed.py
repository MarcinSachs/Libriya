from app.models import Genre, Library, User, Tenant
from app import create_app, db
from flask_babel import _
import sys
import os

# Add the parent directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


genres = [
    _('Business / Self-Help'),
    _('Children'),
    _('Young Adult'),
    _('Fantasy'),
    _('Comic'),
    _('Crime / Thriller'),
    _('Culture / Art'),
    _('Non-fiction'),
    _('Fiction'),
    _('Popular Science'),
    _('Scientific / Academic'),
    _('Poetry / Drama'),
    _('Manual / Education'),
    _('Guide / Hobby'),
    _('Press'),
    _('Religion / Philosophy'),
    _('Romance / Contemporary'),
    _('Others')
]


def seed_database():
    app = create_app()  # Create the Flask app
    with app.app_context():
        # Ensure the `tenant` table has the `updated_at` column (some migrations may not have run)
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        cols = [c['name'] for c in inspector.get_columns('tenant')] if 'tenant' in inspector.get_table_names() else []
        if 'updated_at' not in cols:
            # Add the column in a dialect-aware way
            dialect = db.engine.dialect.name
            if dialect == 'sqlite':
                db.session.execute(text("ALTER TABLE tenant ADD COLUMN updated_at DATETIME"))
            else:
                # MySQL/MariaDB: set default CURRENT_TIMESTAMP and on update
                db.session.execute(
                    text("ALTER TABLE tenant ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"))
            db.session.commit()
        # Ensure 'status' and premium feature columns exist
        needed_cols = {
            'status': "VARCHAR(50) DEFAULT 'active'",
            'premium_bookcover_enabled': 'TINYINT(1) DEFAULT 0',
            'premium_biblioteka_narodowa_enabled': 'TINYINT(1) DEFAULT 0'
        }
        for col, col_def in needed_cols.items():
            if col not in cols:
                dialect = db.engine.dialect.name
                if dialect == 'sqlite':
                    # SQLite: simple ADD COLUMN
                    db.session.execute(text(f"ALTER TABLE tenant ADD COLUMN {col} {col_def}"))
                else:
                    # MySQL/MariaDB: ensure NOT NULL where appropriate
                    db.session.execute(text(f"ALTER TABLE tenant ADD COLUMN {col} {col_def} NOT NULL"))
        db.session.commit()
        # Ensure `user` table has expected columns used by the seed
        user_cols = [c['name'] for c in inspector.get_columns('user')] if 'user' in inspector.get_table_names() else []
        user_needed = {
            'is_email_verified': 'TINYINT(1) DEFAULT 0',
            'image_file': "VARCHAR(50) DEFAULT 'default.jpg'",
            'first_name': 'VARCHAR(50)',
            'last_name': 'VARCHAR(50)',
            'password_hash': 'VARCHAR(255) NOT NULL',
            'role': "VARCHAR(20) DEFAULT 'user'"
        }
        for col, col_def in user_needed.items():
            if col not in user_cols:
                dialect = db.engine.dialect.name
                if dialect == 'sqlite':
                    db.session.execute(text(f"ALTER TABLE user ADD COLUMN {col} {col_def}"))
                else:
                    # MySQL/MariaDB: ensure NOT NULL where appropriate
                    db.session.execute(text(f"ALTER TABLE user ADD COLUMN {col} {col_def}"))
        db.session.commit()
        # --- Ensure Default Tenant Exists ---
        default_tenant = db.session.query(Tenant).filter_by(name='default').first()
        if not default_tenant:
            default_tenant = Tenant(
                name='default',
                subdomain='default'
            )
            db.session.add(default_tenant)
            db.session.commit()
            print("Default tenant created.")
        else:
            # Update subdomain if not set
            if not default_tenant.subdomain:
                default_tenant.subdomain = 'default'
                db.session.commit()
            print("Default tenant already exists.")

        # --- Seed Library ---
        if db.session.query(Library).count() == 0:
            default_library = Library(name="Główna Biblioteka", tenant_id=default_tenant.id)
            db.session.add(default_library)
            db.session.commit()
            print("Default library created.")
        else:
            default_library = db.session.query(Library).first()
            print("Default library already exists.")

        # --- Seed Super-Admin User (role='superadmin', tenant_id=NULL) ---
        super_admin = db.session.query(User).filter_by(username='superadmin').first()
        if not super_admin:
            super_admin = User(
                username='superadmin',
                email='superadmin@example.com',
                role='superadmin',
                tenant_id=None  # Super-admin has NO tenant assigned
            )
            super_admin.set_password('superadmin')
            # Mark seeded user as verified
            super_admin.is_email_verified = True
            db.session.add(super_admin)
            db.session.commit()
            print("Super-admin user created with role='superadmin'.")
        else:
            # Fix if superadmin exists with wrong role or tenant_id
            if super_admin.role != 'superadmin' or super_admin.tenant_id is not None:
                super_admin.role = 'superadmin'
                super_admin.tenant_id = None
            # Ensure seeded user is verified
            super_admin.is_email_verified = True
            db.session.commit()
            print("Super-admin user already exists with correct configuration.")

        # --- Seed Admin User (tenant-specific admin, tenant_id=default_tenant.id) ---
        if db.session.query(User).filter_by(username='admin').count() == 0:
            admin_user = User(
                username='admin',
                email='admin@example.com',
                role='admin',
                tenant_id=default_tenant.id  # Admin for this specific tenant
            )
            admin_user.set_password('admin')
            # Mark seeded user as verified
            admin_user.is_email_verified = True
            # Add user to the default library
            admin_user.libraries.append(default_library)
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created for default tenant.")
        else:
            existing_admin = db.session.query(User).filter_by(username='admin').first()
            existing_admin.is_email_verified = True
            db.session.commit()
            print("Admin user already exists.")

        # --- Seed Manager User ---
        if db.session.query(User).filter_by(username='manager').count() == 0:
            manager_user = User(
                username='manager',
                email='manager@example.com',
                role='manager',
                tenant_id=default_tenant.id
            )
            manager_user.set_password('manager')
            # Mark seeded user as verified
            manager_user.is_email_verified = True
            # Add manager to the default library
            manager_user.libraries.append(default_library)
            db.session.add(manager_user)
            db.session.commit()
            print("Manager user created and assigned to the default library.")
        else:
            existing_manager = db.session.query(User).filter_by(username='manager').first()
            existing_manager.is_email_verified = True
            db.session.commit()
            print("Manager user already exists.")

        # --- Seed Regular User ---
        if db.session.query(User).filter_by(username='user').count() == 0:
            regular_user = User(
                username='user',
                email='user@example.com',
                role='user',
                tenant_id=default_tenant.id
            )
            regular_user.set_password('user')
            # Mark seeded user as verified
            regular_user.is_email_verified = True
            # Add user to the default library
            regular_user.libraries.append(default_library)
            db.session.add(regular_user)
            db.session.commit()
            print("Regular user created and assigned to the default library.")
        else:
            existing_user = db.session.query(User).filter_by(username='user').first()
            existing_user.is_email_verified = True
            db.session.commit()
            print("Regular user already exists.")

        # --- Seed Genres ---
        # Remove existing genres
        db.session.query(Genre).delete()
        db.session.commit()
        print("Genre table cleared.")

        # Add genres
        for genre_name in genres:
            # use str() to convert genre_name to string
            genre = Genre(name=str(genre_name))
            db.session.add(genre)
        db.session.commit()
        print("Genres added to the database.")


if __name__ == '__main__':
    seed_database()
