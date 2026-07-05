from flask import Blueprint

api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")

from app.api.v1.auth import auth_bp  # noqa: E402

api_v1.register_blueprint(auth_bp)
