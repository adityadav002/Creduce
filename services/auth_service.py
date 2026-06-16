import bcrypt
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
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
            (name, email, hashed_pw)
        )
        db.commit()
        return True

    except Exception as e:
        db.rollback()
        raise e

    finally:
        close_connection(cursor, db)


def authenticate_user(email, password):
    """
    Verify email/password against the database.
    Returns the user row on success, None if not found, False if wrong password.
    Moved from app.py /login POST handler.
    """
    cursor, db = get_cursor()
    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user is None:
            return None

        stored_password = user[3]

        if bcrypt.checkpw(password.encode("utf-8"), stored_password.encode("utf-8")):
            return user

        return False

    finally:
        close_connection(cursor, db)