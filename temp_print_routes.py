from app import create_app
app = create_app()
with app.test_request_context():
    rules = sorted(app.url_map.iter_rules(), key=lambda r: r.rule)
    for r in rules:
        print(r.rule, sorted(list(r.methods)))
