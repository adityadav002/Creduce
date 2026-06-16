from utils.db import get_cursor, close_connection


def get_user_profile(user_id):
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