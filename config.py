# config.py

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_key")

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASS = os.getenv("DB_PASS", "")
    DB_NAME = os.getenv("DB_NAME", "expense_tracker")
    DB_PORT = int(os.getenv("DB_PORT", 3306))

    MYSQL_URL = os.getenv("MYSQL_URL")