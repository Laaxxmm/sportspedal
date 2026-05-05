from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
import os

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')

    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data'), exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    # Context processor
    @app.context_processor
    def inject_permissions():
        from flask_login import current_user
        from app.models import PERMISSION_KEYS
        return {'PERMISSION_KEYS': PERMISSION_KEYS}

    # Error handler (shows error to logged-in superadmin only)
    @app.errorhandler(500)
    def handle_500(e):
        import traceback
        from flask_login import current_user as cu
        if cu and cu.is_authenticated and cu.is_superadmin:
            return f"<pre>{traceback.format_exc()}</pre>", 500
        return "Something went wrong. Please try again.", 500

    # Security headers
    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    # Exempt AJAX endpoints from CSRF where needed
    from app.routes.api import bp as api_bp
    csrf.exempt(api_bp)

    # Register blueprints
    from app.routes.auth import bp as auth_bp
    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.products import bp as products_bp
    from app.routes.purchases import bp as purchases_bp
    from app.routes.sales import bp as sales_bp
    from app.routes.customers import bp as customers_bp
    from app.routes.suppliers import bp as suppliers_bp
    from app.routes.inventory import bp as inventory_bp
    from app.routes.settings import bp as settings_bp
    from app.routes.users import bp as users_bp
    from app.routes.transfers import bp as transfers_bp
    from app.routes.payments import bp as payments_bp
    from app.routes.supplier_portal import bp as supplier_portal_bp
    from app.routes.adjustments import bp as adjustments_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(products_bp, url_prefix='/products')
    app.register_blueprint(purchases_bp, url_prefix='/purchases')
    app.register_blueprint(sales_bp, url_prefix='/sales')
    app.register_blueprint(customers_bp, url_prefix='/customers')
    app.register_blueprint(suppliers_bp, url_prefix='/suppliers')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(api_bp)
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(transfers_bp, url_prefix='/transfers')
    app.register_blueprint(payments_bp, url_prefix='/payments')
    app.register_blueprint(supplier_portal_bp)
    app.register_blueprint(adjustments_bp, url_prefix='/adjustments')

    return app
