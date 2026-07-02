from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Extensions are *instantiated* here, unconfigured, and *initialised* against the
# application inside the factory (Backend Architecture §1). No app config,
# connection, or binding happens at import time — that is the factory's job, so
# the same extension objects can be reused across app instances (tests, CLI).
db = SQLAlchemy()
migrate = Migrate()


# ---------------------------------------------------------------------------
# Stubs — replaced with real instances once the packages are installed.
# Each follows the Flask extension pattern: instantiate here, call
# init_app(app) inside create_app().
# ---------------------------------------------------------------------------

class _RedisStub:
    """Placeholder until flask-redis / redis-py is wired."""

    def init_app(self, app):
        pass


class _CeleryStub:
    """Placeholder until Celery is wired."""

    def init_app(self, app):
        pass


class _JWTStub:
    """Placeholder until Flask-JWT-Extended is wired."""

    def init_app(self, app):
        pass


class _LimiterStub:
    """Placeholder until Flask-Limiter is wired."""

    def init_app(self, app):
        pass


redis_client = _RedisStub()
celery = _CeleryStub()
jwt = _JWTStub()
limiter = _LimiterStub()