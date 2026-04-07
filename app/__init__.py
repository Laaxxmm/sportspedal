from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')

    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data'), exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)

    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.products import bp as products_bp
    from app.routes.purchases import bp as purchases_bp
    from app.routes.sales import bp as sales_bp
    from app.routes.customers import bp as customers_bp
    from app.routes.suppliers import bp as suppliers_bp
    from app.routes.inventory import bp as inventory_bp
    from app.routes.settings import bp as settings_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(products_bp, url_prefix='/products')
    app.register_blueprint(purchases_bp, url_prefix='/purchases')
    app.register_blueprint(sales_bp, url_prefix='/sales')
    app.register_blueprint(customers_bp, url_prefix='/customers')
    app.register_blueprint(suppliers_bp, url_prefix='/suppliers')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(settings_bp, url_prefix='/settings')

    return app
