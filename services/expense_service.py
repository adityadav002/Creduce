from utils.db import get_cursor, close_connection
from services.prediction_service import predict_category


def add_expense(user_id, date, amount, note, payment, category):
    cursor, db = get_cursor()

    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        resolved_category = (
            category or
            (predict_category(note) if note else "other")
        )

        cursor.execute(
            """
            INSERT INTO expenses
            (exp_date, category, amount, note, pay_method, user_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                date,
                resolved_category,
                amount,
                note,
                payment,
                user_id
            )
        )

        db.commit()

    finally:
        close_connection(cursor, db)


def delete_expense(expense_id, user_id):
    cursor, db = get_cursor()

    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        cursor.execute(
            "DELETE FROM expenses WHERE id=%s AND user_id=%s",
            (expense_id, user_id)
        )

        db.commit()

    finally:
        close_connection(cursor, db)


def get_expense_by_id(expense_id, user_id):
    cursor, db = get_cursor()

    if cursor is None:
        return None

    try:
        cursor.execute(
            "SELECT * FROM expenses WHERE id=%s AND user_id=%s",
            (expense_id, user_id)
        )

        return cursor.fetchone()

    finally:
        close_connection(cursor, db)


def update_expense(
    expense_id,
    user_id,
    date,
    category,
    amount,
    note,
    payment
):
    cursor, db = get_cursor()

    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        cursor.execute(
            """
            UPDATE expenses
            SET exp_date=%s,
                category=%s,
                amount=%s,
                note=%s,
                pay_method=%s
            WHERE id=%s
            AND user_id=%s
            """,
            (
                date,
                category,
                amount,
                note,
                payment,
                expense_id,
                user_id
            )
        )

        db.commit()

    finally:
        close_connection(cursor, db)