import pandas as pd
from utils.dataframe_helper import fetch_df
from utils.date_helper import get_date_context
from services.budget_service import get_monthly_budget
from services.prediction_service import predict_monthly_expense

def get_dashboard_data(user_id):
    """
    Compute all data required by dashboard.html.
    """
    date_ctx = get_date_context()
    now = date_ctx["now"]

    total = avg = count = 0
    max_amount, max_note = 0, "N/A"
    top_category = top_amount = low_category = low_amount = None
    remaining_spending = 0
    over_spending = 0
    predicted_expense = 0
    today_total = week_total = month_total = year_total = 0

    monthly_budget = get_monthly_budget(user_id)
    monthly_budget = float(monthly_budget or 0)

    try:
        df = fetch_df(
            """
            SELECT e.*, COALESCE(c.name, 'Other') AS category
            FROM expenses e
            LEFT JOIN categories c ON e.category_id = c.id
            WHERE e.user_id = %s AND e.type = 'expense'
            """,
            (user_id,)
        )
    except Exception as e:
        print(f"FETCH ERROR: {e}")
        df = pd.DataFrame()

    if not df.empty:
        df["exp_date"] = pd.to_datetime(df["exp_date"])

        today_df = df[df["exp_date"].dt.date == now.date()]
        today_total = float(today_df["amount"].sum()) if not today_df.empty else 0

        week_df = df[
            (df["exp_date"] >= date_ctx["start_of_week"]) &
            (df["exp_date"] <= date_ctx["end_of_week"])
        ]
        week_total = float(week_df["amount"].sum()) if not week_df.empty else 0

        month_df = df[
            (df["exp_date"].dt.month == now.month) &
            (df["exp_date"].dt.year == now.year)
        ]
        month_total = float(month_df["amount"].sum()) if not month_df.empty else 0

        year_df = df[df["exp_date"].dt.year == now.year]
        year_total = float(year_df["amount"].sum()) if not year_df.empty else 0

        monthly_df = month_df

        if not monthly_df.empty:
            total = float(monthly_df["amount"].sum())
            avg = float(round(monthly_df["amount"].mean(), 2))
            count = int(monthly_df["amount"].count())

            try:
                max_row = monthly_df.loc[monthly_df["amount"].idxmax()]
                max_amount = float(max_row["amount"])
                max_note = max_row["note"]
            except Exception:
                max_amount, max_note = 0, "N/A"

            category_totals = monthly_df.groupby("category")["amount"].sum()
            if not category_totals.empty:
                top_category = category_totals.idxmax()
                top_amount = float(category_totals.max())
                low_category = category_totals.idxmin()
                low_amount = float(category_totals.min())

        remaining_spending = monthly_budget - total
        over_spending = total - monthly_budget

        predicted_expense = predict_monthly_expense(df)

    return {
        "total": total,
        "average": avg,
        "count": count,
        "max_amount": max_amount,
        "max_note": max_note,
        "top_category": top_category,
        "top_amount": top_amount,
        "low_category": low_category,
        "low_amount": low_amount,
        "monthly_budget": monthly_budget,
        "remaining_spending": remaining_spending,
        "over_spending": over_spending,
        "predicted_expense": predicted_expense,
        "today_total": today_total,
        "week_total": week_total,
        "month_total": month_total,
        "year_total": year_total,
        "today_label": date_ctx["today_label"],
        "week_range": date_ctx["week_range"],
        "month_range": date_ctx["month_range"],
        "year_label": date_ctx["year_label"],
        "current_month_name": date_ctx["current_month_name"],
    }

def get_account_dashboard_summary(user_id: int) -> dict:
    """
    Aggregate data for the multi-account dashboard view.

    Returns:
        total_balance       — sum of current_balance across all accounts
        account_summary     — list of (name, type, current_balance) rows
        recent_transactions — last 15 transactions with joined labels
    """
    from utils.db import get_cursor, close_connection

    cursor, db = get_cursor()
    if cursor is None:
        return {"total_balance": 0.0, "account_summary": [], "recent_transactions": []}

    try:
        cursor.execute(
            "SELECT COALESCE(SUM(current_balance), 0) FROM accounts WHERE user_id = %s",
            (user_id,)
        )
        total_balance = float(cursor.fetchone()[0])

        cursor.execute(
            "SELECT name, type, current_balance FROM accounts WHERE user_id = %s ORDER BY name",
            (user_id,)
        )
        account_summary = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                e.exp_date,
                e.amount,
                e.type,
                a.name AS account_name,
                c.name AS category_name,
                sc.name AS subcategory_name
            FROM expenses e
            JOIN accounts a
                ON a.id = e.account_id
            LEFT JOIN categories c
                ON c.id = e.category_id
            LEFT JOIN subcategories sc
                ON sc.id = e.subcategory_id
            WHERE e.user_id=%s
            ORDER BY e.exp_date DESC,e.id DESC
            LIMIT 15
            """,
            (user_id,)
        )
        recent_transactions = cursor.fetchall()

        return {
            "total_balance": total_balance,
            "account_summary": account_summary,
            "recent_transactions": recent_transactions,
        }

    finally:
        close_connection(cursor, db)
