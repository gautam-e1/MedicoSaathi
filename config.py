import os

BASE_DIR = os.path.abspath(
    os.path.dirname(__file__)
)

class Config:

    SECRET_KEY = "super-secret-key"

    MAX_CONTENT_LENGTH = 2 * 1024 * 1024

    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:gautam321@localhost:5432/medical_shop"

    SQLALCHEMY_TRACK_MODIFICATIONS = False