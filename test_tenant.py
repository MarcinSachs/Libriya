from app import create_app
app = create_app()
with app.app_context():
    from app.models import Tenant
    t = Tenant.query.get(1)
    print(f"Tenant 1: {t}")
    if t:
        print(f"  ID: {t.id}, Name: {t.name}, premium_bookcover_enabled: {t.premium_bookcover_enabled}")
        print(f"  premium_biblioteka_narodowa_enabled: {t.premium_biblioteka_narodowa_enabled}")
