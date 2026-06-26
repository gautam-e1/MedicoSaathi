from flask import Flask

from config import Config

from app.extensions.extensions import db

from flask_migrate import Migrate


def create_app():

    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static"
    )

    app.config.from_object(Config)

    db.init_app(app)

    Migrate(app, db)

    # Import models inside app context
    with app.app_context():
        from app.models.models import (
            Medicine,
            Bill,
            Wholesaler,
            Order,
            Shop,
            User,
            Customer
        )

    # Import blueprints
    from app.routes.dashboard import dashboard_bp
    from app.routes.medicines import medicines_bp
    from app.routes.billing import billing_bp
    from app.routes.wholesalers import wholesalers_bp
    from app.routes.customers import customers_bp
    from app.routes.orders import orders_bp
    from app.routes.auth import auth_bp

    # Register blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(medicines_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(wholesalers_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(
    customers_bp,
    url_prefix="/api"
)

    return app