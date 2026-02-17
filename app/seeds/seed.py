import sys
import os

# Add the parent directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from flask_babel import _
from app import create_app, db
from app.models import Genre, Library, User, Tenant


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

        # --- Seed Super-Admin User (tenant_id=NULL) ---
        if db.session.query(User).filter_by(username='superadmin').count() == 0:
            super_admin = User(
                username='superadmin',
                email='superadmin@example.com',
                role='admin',
                tenant_id=None  # Super-admin has NO tenant assigned
            )
            super_admin.set_password('superadmin')
            db.session.add(super_admin)
            db.session.commit()
            print("Super-admin user created (manages all tenants).")
        else:
            print("Super-admin user already exists.")

        # --- Seed Admin User (tenant-specific admin, tenant_id=default_tenant.id) ---
        if db.session.query(User).filter_by(username='admin').count() == 0:
            admin_user = User(
                username='admin',
                email='admin@example.com',
                role='admin',
                tenant_id=default_tenant.id  # Admin for this specific tenant
            )
            admin_user.set_password('admin')
            # Add user to the default library
            admin_user.libraries.append(default_library)
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created for default tenant.")
        else:
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
            # Add manager to the default library
            manager_user.libraries.append(default_library)
            db.session.add(manager_user)
            db.session.commit()
            print("Manager user created and assigned to the default library.")
        else:
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
            # Add user to the default library
            regular_user.libraries.append(default_library)
            db.session.add(regular_user)
            db.session.commit()
            print("Regular user created and assigned to the default library.")
        else:
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
