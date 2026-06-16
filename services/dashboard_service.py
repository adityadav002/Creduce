import pandas as pd
from utils.dataframe_helper import fetch_df
from utils.date_helper import get_date_context
from services.budget_service import get_monthly_budget
from services.prediction_service import predict_monthly_expense

def get_dashboard_data(user_id):
    """
    Compute all data required by dashboard.html.

    Aggregates:
    - Expense statistics (total, average, count)
    - Maximum expense (max_amount, max_note)
    - Category analysis (top_category, top_amount, low_category, low_amount)
    - Budget calculations (monthly_budget, remaining_spending, over_spending)
    - Time statistics (today_total, week_total, month_total, year_total)
    - Labels (today_label, week_range, month_range, year_label, current_month_name)
    - ML prediction (predicted_expense)

    All logic moved from app.py main() route.
    """
    date_ctx = get_date_context()
    now = date_ctx["now"]

    # Initialize all variables
    total = avg = count = 0
    max_amount, max_note = 0, "N/A"
    top_category = top_amount = low_category = low_amount = None
    remaining_spending = 0
    over_spending = 0
    predicted_expense = 0
    today_total = week_total = month_total = year_total = 0

    # Fetch budget
    monthly_budget = get_monthly_budget(user_id)

    # Fetch all expenses for this user
    try:
        df = fetch_df(
            "SELECT * FROM expenses WHERE user_id = %s",
            (user_id,)
        )
    except Exception as e:
        print(f"FETCH ERROR: {e}")
        df = pd.DataFrame()

    if not df.empty:
        df["exp_date"] = pd.to_datetime(df["exp_date"])

        # ---- Time-period totals ----

        # Today
        today_df = df[df["exp_date"].dt.date == now.date()]
        today_total = float(today_df["amount"].sum()) if not today_df.empty else 0

        # This Week (Mon–Sun)
        week_df = df[
            (df["exp_date"] >= date_ctx["start_of_week"]) &
            (df["exp_date"] <= date_ctx["end_of_week"])
        ]
        week_total = float(week_df["amount"].sum()) if not week_df.empty else 0

        # This Month
        month_df = df[
            (df["exp_date"].dt.month == now.month) &
            (df["exp_date"].dt.year == now.year)
        ]
        month_total = float(month_df["amount"].sum()) if not month_df.empty else 0

        # This Year
        year_df = df[df["exp_date"].dt.year == now.year]
        year_total = float(year_df["amount"].sum()) if not year_df.empty else 0

        # ---- Monthly statistics ----
        monthly_df = month_df  # already filtered above

        if not monthly_df.empty:
            total = float(monthly_df["amount"].sum())
            avg = float(round(monthly_df["amount"].mean(), 2))
            count = int(monthly_df["amount"].count())

            # Max expense
            try:
                max_row = monthly_df.loc[monthly_df["amount"].idxmax()]
                max_amount = float(max_row["amount"])
                max_note = max_row["note"]
            except Exception:
                max_amount, max_note = 0, "N/A"

            # Category analysis
            category_totals = monthly_df.groupby("category")["amount"].sum()
            if not category_totals.empty:
                top_category = category_totals.idxmax()
                top_amount = float(category_totals.max())
                low_category = category_totals.idxmin()
                low_amount = float(category_totals.min())

        # ---- Budget calculations ----
        remaining_spending = monthly_budget - total
        over_spending = total - monthly_budget

        # ---- ML Prediction ----
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