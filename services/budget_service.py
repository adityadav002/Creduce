from utils.db import get_cursor, close_connection


def save_monthly_budget(user_id, budget_amount):
    """
    Insert or update the monthly budget for a user.
    Moved from app.py /profile POST handler and existing services/budget_service.py stub.
    """
    cursor, db = get_cursor()
    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        cursor.execute(
            """
            INSERT INTO budget (user_id, budget_amount)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE budget_amount = %s
            """,
            (user_id, budget_amount, budget_amount)
        )
        db.commit()

    finally:
        close_connection(cursor, db)


def get_monthly_budget(user_id):
    """
    Retrieve the current monthly budget for a user.
    Returns the budget amount as a float, or 0 if not set.
    Moved from app.py main() budget fetch block.
    """
    cursor, db = get_cursor()
    if cursor is None:
        return 0

    try:
        cursor.execute(
            "SELECT budget_amount FROM budget WHERE user_id = %s LIMIT 1",
            (user_id,)
        )
        row = cursor.fetchone()
        return row[0] if row else 0

    except Exception as e:
        print(f"BUDGET ERROR: {e}")
        return 0

    finally:
        close_connection(cursor, db)