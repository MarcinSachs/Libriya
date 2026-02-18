from app import db, create_app
app = create_app()
app.app_context().push()
from app.models import User, Tenant

print("=== TENANTS ===")
tenants = Tenant.query.all()
for t in tenants:
    print(f"ID: {t.id}, Name: {t.name}, Subdomain: {t.subdomain}")

print("\n=== USERS ===")
users = User.query.all()
for u in users:
    print(f"ID: {u.id}, Username: {u.username}, Email: {u.email}, Role: {u.role}, Tenant_ID: {u.tenant_id}")

print("\n=== LIBRARIES ===")
from app.models import Library
libs = Library.query.all()
for lib in libs:
    print(f"ID: {lib.id}, Name: {lib.name}, Tenant_ID: {lib.tenant_id}")
