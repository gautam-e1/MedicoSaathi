import os
import sys

from flask import Flask

from config import config_by_name

from app.extensions.extensions import (
    db, migrate, redis_client, celery, jwt, limiter,
)


def create_app(config_name=None):

    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static"
    )

    app.config.from_object(
        config_by_name.get(config_name, config_by_name["default"])
    )

    # --- Centralized logging ---
    from app.core.logging import setup_logging
    setup_logging(app)

    # --- Startup config validation ---
    _validate_config(app)

    # Initialise extensions against this app instance (Backend Architecture §1).
    db.init_app(app)
    migrate.init_app(app, db)
    redis_client.init_app(app)
    celery.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

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

    # --- Global error handlers ---
    from app.core.errors import register_error_handlers
    register_error_handlers(app)

    # --- Health endpoints ---
    from app.core.health import health_bp
    app.register_blueprint(health_bp)

    # Legacy blueprints
    from app.routes.dashboard import dashboard_bp
    from app.routes.medicines import medicines_bp
    from app.routes.billing import billing_bp
    from app.routes.wholesalers import wholesalers_bp
    from app.routes.customers import customers_bp
    from app.routes.orders import orders_bp
    from app.routes.auth import auth_bp

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

    # API v1 blueprint shell (no live routes yet)
    from app.api.v1 import api_v1
    app.register_blueprint(api_v1)

    # --- Startup verification ---
    _verify_startup(app)

    return app


def _validate_config(app):
    required = ["SECRET_KEY", "SQLALCHEMY_DATABASE_URI"]
    missing = [k for k in required if not app.config.get(k)]
    if missing:
        app.logger.critical(
            "Missing required config: %s", ", ".join(missing)
        )
        sys.exit(1)


def _verify_startup(app):
    from sqlalchemy import text

    with app.app_context():
        try:
            db.session.execute(text("SELECT 1"))
            app.logger.info("Database connection verified")
        except Exception as e:
            app.logger.critical("Database connection failed: %s", e)
            sys.exit(1)

    bp_names = list(app.blueprints.keys())
    app.logger.info(
        "Registered blueprints: %s", ", ".join(bp_names)
    )