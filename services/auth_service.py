import bcrypt
import mysql.connector
from utils.db import get_cursor, close_connection


def register_user(name, email, password):
    """
    Insert a new user into the database with a hashed password.
    Returns True on success, raises Exception on failure.
    Moved from app.py /register POST handler.
    """
    cursor, db = get_cursor()
    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        cleaned_name = (name or "").strip()
        cleaned_email = (email or "").strip().lower()
        if not cleaned_name or not cleaned_email or not password:
            raise ValueError("Name, email, and password are required")

        hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
            (cleaned_name, cleaned_email, hashed_pw)
        )
        db.commit()
        return True

    except mysql.connector.IntegrityError:
        db.rollback()
        return False
    except Exception:
        db.rollback()
        raise

    finally:
        close_connection(cursor, db)


def authenticate_user(email, password):
    """
    Verify email/password against the database.
    Returns the user row on success, None if not found, False if wrong password.
    Moved from app.py /login POST handler.
    """
    if not email or not password:
        raise ValueError("Email and password are required")

    cursor, db = get_cursor()
    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        cleaned_email = (email or "").strip().lower()
        cursor.execute("SELECT * FROM users WHERE email = %s", (cleaned_email,))
        user = cursor.fetchone()

        if user is None:
            return None

        stored_password = user[3]
        if isinstance(stored_password, str):
            stored_password = stored_password.encode("utf-8")

        if bcrypt.checkpw(password.encode("utf-8"), stored_password):
            return user

        return False

    finally:
        close_connection(cursor, db)
