from app import create_app, db

app = create_app()
with app.app_context():
    print('Database URL:', db.engine.url)
    print('Dialect:', db.engine.dialect.name)
