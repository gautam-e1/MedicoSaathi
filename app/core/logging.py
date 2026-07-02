import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, request


def setup_logging(app: Flask) -> None:
    log_dir = app.config.get("LOG_DIR", "logs")
    log_level_name = app.config.get("LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)

    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    )

    # --- app.log: INFO and above ---
    app_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    app_handler.setLevel(log_level)
    app_handler.setFormatter(formatter)

    # --- error.log: ERROR and above ---
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, "error.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    app.logger.setLevel(log_level)
    app.logger.addHandler(app_handler)
    app.logger.addHandler(error_handler)

    _register_request_logging(app)

    app.logger.info(
        "Application starting — env=%s, debug=%s",
        app.config.get("ENV_NAME", "development"),
        app.debug,
    )


def _register_request_logging(app: Flask) -> None:

    @app.after_request
    def log_request(response):
        app.logger.info(
            "%s %s %s",
            request.method,
            request.path,
            response.status_code,
        )
        return response
