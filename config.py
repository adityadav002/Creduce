# config.py

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_key")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASS = os.getenv("DB_PASS", "")
    DB_NAME = os.getenv("DB_NAME", "expense_tracker")
    DB_PORT = int(os.getenv("DB_PORT", 3306))

    MYSQL_URL = os.getenv("MYSQL_URL")
    MODEL_PATH = os.getenv("MODEL_PATH", os.path.join("ml", "trained_model.pkl"))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "1") == "1"


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
