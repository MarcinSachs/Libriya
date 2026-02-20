from app.routes.main import bp as main_bp
from app.routes.auth import bp as auth_bp
from app.routes.users import bp as users_bp
from app.routes.books import bp as books_bp
from app.routes.libraries import bp as libraries_bp
from app.routes.loans import bp as loans_bp
from app.routes.invitations import bp as invitations_bp
from app.routes.admin import bp as admin_bp
from app.routes.messaging import bp as messaging_bp
from app.routes.share import bp as share_bp


def register_blueprints(app):
    """Register all blueprints with the Flask app."""
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(libraries_bp)
    app.register_blueprint(loans_bp)
    app.register_blueprint(invitations_bp)
    app.register_blueprint(share_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(messaging_bp)
