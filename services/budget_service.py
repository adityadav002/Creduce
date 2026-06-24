import datetime
from utils.db import get_cursor, close_connection


def save_monthly_budget(user_id, budget_amount):
    """
    Insert or update the monthly budget for a user.
    """
    cursor, db = get_cursor()
    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        amount = float(budget_amount or 0)
        current_month = datetime.datetime.now().strftime("%Y-%m")

        cursor.execute(
            "SELECT id FROM budget WHERE user_id = %s AND month = %s",
            (user_id, current_month)
        )
        row = cursor.fetchone()

        if row:
            cursor.execute(
                "UPDATE budget SET budget_amount = %s WHERE id = %s",
                (amount, row[0])
            )
        else:
            cursor.execute(
                "INSERT INTO budget (user_id, month, budget_amount) VALUES (%s, %s, %s)",
                (user_id, current_month, amount)
            )

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        close_connection(cursor, db)


def get_monthly_budget(user_id):
    """
    Retrieve the current monthly budget for a user.
    Returns the budget amount as a float, or 0 if not set.
    """
    cursor, db = get_cursor()
    if cursor is None:
        return 0

    try:
        current_month = datetime.datetime.now().strftime("%Y-%m")
        cursor.execute(
            "SELECT budget_amount FROM budget WHERE user_id = %s AND month = %s LIMIT 1",
            (user_id, current_month)
        )
        row = cursor.fetchone()
        return float(row[0]) if row else 0

    except Exception as e:
        print(f"BUDGET ERROR: {e}")
        return 0

    finally:
        close_connection(cursor, db)
