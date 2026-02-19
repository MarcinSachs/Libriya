from app import create_app
app = create_app()
with app.app_context():
    from app.models import User
    # Sprawdzam pierwszego użytkownika
    u = User.query.first()
    print(f"User: {u}")
    if u:
        print(f"  Username: {u.username}, Role: {u.role}, is_super_admin: {u.is_super_admin}")
