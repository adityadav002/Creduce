import pandas as pd
from datetime import datetime
from utils.db import get_cursor, close_connection
from utils.dataframe_helper import fetch_df


def get_transaction_history(user_id):
    """
    Fetch all expenses for a user ordered by date descending.
    Moved from app.py /transaction_detail route.
    """
    cursor, db = get_cursor()
    if cursor is None:
        return []

    try:
        cursor.execute(
            "SELECT * FROM expenses WHERE user_id = %s ORDER BY exp_date DESC",
            (user_id,)
        )
        return cursor.fetchall()

    finally:
        close_connection(cursor, db)


def filter_transactions(user_id, category, month, payment):
    """
    Filter expenses by category, month, and/or payment method.
    Returns an empty list when no filters are supplied.
    Moved from app.py /filter_transaction route.
    """
    cursor, db = get_cursor()
    if cursor is None:
        return []

    try:
        # If no filters → show empty state
        if not category and not month and not payment:
            return []

        query = "SELECT * FROM expenses WHERE user_id = %s"
        params = [user_id]

        if category and category != "all":
            query += " AND category = %s"
            params.append(category)

        if payment and payment != "all":
            query += " AND pay_method = %s"
            params.append(payment)

        if month and month != "all":
            query += " AND MONTH(exp_date) = %s"
            params.append(int(month))

        query += " ORDER BY exp_date DESC"

        cursor.execute(query, tuple(params))
        return cursor.fetchall()

    finally:
        close_connection(cursor, db)


def monthly_transaction_details(user_id):
    """
    Return a dict of {category: [list of expense records]} for the current month.
    Moved from app.py /monthly_transaction route.
    """
    now = datetime.now()

    df = fetch_df(
        "SELECT * FROM expenses WHERE user_id = %s",
        (user_id,)
    )

    if df.empty:
        return {}

    df["exp_date"] = pd.to_datetime(df["exp_date"])
    monthly_df = df[
        (df["exp_date"].dt.month == now.month) &
        (df["exp_date"].dt.year == now.year)
    ]

    category_details = (
        monthly_df.groupby("category")
        .apply(lambda x: x[["amount", "note", "pay_method", "exp_date"]].to_dict("records"))
        .to_dict()
    )

    return category_details