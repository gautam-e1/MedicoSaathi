from flask import Blueprint, jsonify
from sqlalchemy import text

from app.extensions.extensions import db

health_bp = Blueprint("health", __name__)


@health_bp.route("/health")
def health():
    checks = {
        "flask": True,
        "database": _check_db(),
    }
    healthy = all(checks.values())
    return jsonify({
        "status": "healthy" if healthy else "unhealthy",
        "checks": checks,
    }), 200 if healthy else 503


@health_bp.route("/ready")
def ready():
    db_ok = _check_db()
    ready = db_ok
    return jsonify({
        "status": "ready" if ready else "not_ready",
        "checks": {
            "database": db_ok,
        },
    }), 200 if ready else 503


@health_bp.route("/live")
def live():
    return jsonify({
        "status": "alive",
    }), 200


def _check_db():
    try:
        db.session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
