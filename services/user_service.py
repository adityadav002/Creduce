from utils.db import get_cursor, close_connection


def get_user_profile(user_id):
    """Return the current user's profile fields."""
    cursor, db = get_cursor()

    if cursor is None:
        return None

    try:
        cursor.execute(
            """
            SELECT name, email
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )

        row = cursor.fetchone()

        if row:
            return {
                "name": row[0],
                "email": row[1]
            }

        return None

    finally:
        close_connection(cursor, db)


def update_user_profile(user_id, name, email):
    """Update the current user's display name and email address."""
    cursor, db = get_cursor()

    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        cleaned_name = (name or "").strip()
        cleaned_email = (email or "").strip().lower()
        if not cleaned_name or not cleaned_email:
            raise ValueError("Name and email are required")

        cursor.execute(
            """
            UPDATE users
            SET name = %s, email = %s
            WHERE id = %s
            """,
            (cleaned_name, cleaned_email, user_id)
        )
        db.commit()
        return cursor.rowcount > 0

    except Exception:
        db.rollback()
        raise

    finally:
        close_connection(cursor, db)
