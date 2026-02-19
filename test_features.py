from app import create_app
app = create_app()
with app.app_context():
    from app.services.premium.manager import PremiumManager
    features = PremiumManager.list_features()
    print("Features returned by PremiumManager.list_features():")
    for fid, info in features.items():
        print(f"  feature_id: {fid} (type: {type(fid).__name__})")
        print(f"    name: {info.get('name')}")
        print(f"    enabled: {info.get('enabled')}")
