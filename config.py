import os

BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)


class Config:

    APP_NAME = "MedicoSaathi"

    SECRET_KEY = os.environ.get(
        "SECRET_KEY", "super-secret-key"
    )

    MAX_CONTENT_LENGTH = 2 * 1024 * 1024

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:gautam321@localhost:5432/medical_shop"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_URL = os.environ.get(
        "REDIS_URL", "redis://localhost:6379/0"
    )

    LOG_DIR = os.environ.get(
        "LOG_DIR", os.path.join(BASE_DIR, "logs")
    )

    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    ENV_NAME = "base"


class DevelopmentConfig(Config):

    DEBUG = True
    ENV_NAME = "development"
    LOG_LEVEL = "DEBUG"


class StagingConfig(Config):

    DEBUG = False
    TESTING = False
    ENV_NAME = "staging"
    LOG_LEVEL = "INFO"


class ProductionConfig(Config):

    DEBUG = False
    TESTING = False
    ENV_NAME = "production"
    LOG_LEVEL = "WARNING"


config_by_name = {
    "development": DevelopmentConfig,
    "staging": StagingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}