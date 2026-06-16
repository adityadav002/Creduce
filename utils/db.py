import os
import mysql.connector
from urllib.parse import urlparse


def get_db_connection():
    """Create and return a new database connection"""

    try:
        db_url = os.environ.get("MYSQL_URL")

        if db_url:
            # Production
            url = urlparse(db_url)

            db = mysql.connector.connect(
                host=url.hostname,
                port=url.port or 3306,
                user=url.username,
                password=url.password,
                database=url.path[1:] if url.path else None
            )

        else:
            # Local development
            db = mysql.connector.connect(
                host=os.environ.get("DB_HOST", "localhost"),
                user=os.environ.get("DB_USER", "root"),
                password=os.environ.get("DB_PASS", ""),
                database=os.environ.get("DB_NAME", "expense_tracker"),
                port=int(os.environ.get("DB_PORT", 3306))
            )

        print("✅ Database connected successfully")
        return db

    except Exception as e:
        print(f"❌ DB CONNECTION ERROR: {e}")
        return None


def get_cursor(dictionary=False):
    """Get cursor and database connection"""

    db = get_db_connection()

    if db is None:
        return None, None

    cursor = db.cursor(dictionary=dictionary)

    return cursor, db


def close_connection(cursor=None, db=None):
    """Safely close cursor and database connection"""

    if cursor:
        cursor.close()

    if db and db.is_connected():
        db.close()  