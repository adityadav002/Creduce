import calendar
from datetime import datetime
import pandas as pd
from utils.dataframe_helper import fetch_df

def transaction_analysis_service(user_id):
    """
    Returns a 5-tuple:
        category_totals_dict
        month_amounts
        subcategory_totals_dict   (NEW)
        account_totals_dict       (NEW)
        payment_totals_dict       (NEW)

    NOTE: this function used to return a 2-tuple
    (category_totals_dict, month_amounts). Since 3 new dicts were added
    to support the new cards, any route that currently does:
        category_totals_dict, month_amounts = transaction_analysis_service(user_id)
    will need to be updated to unpack all 5 values, e.g.:
        category_totals_dict, month_amounts, subcategory_totals_dict, \\
            account_totals_dict, payment_totals_dict = transaction_analysis_service(user_id)
    and pass the 3 new dicts into render_template() alongside the
    existing two. That route file is outside the scope of this change,
    so it isn't edited here - just flagging the required follow-up.
    """
    now = datetime.now()

    # --- CHANGED: this single query now joins `accounts`, `categories`,
    # and `subcategories` (previously only `categories` was joined, and
    # only to build category_totals_dict). All four current-month
    # aggregates below (category, subcategory, account, payment) are
    # derived from this one dataframe instead of four separate queries,
    # since they all share the same WHERE filters (same user, same
    # month/year, type='expense').
    #
    # COALESCE is used for account/category (and pay_method) so a
    # missing/NULL lookup still groups into a labeled "Unknown"/"Other"
    # bucket instead of silently dropping the row or producing a NULL
    # group key. `subcategory` is intentionally left NULL-able (not
    # COALESCE'd) - rows with no subcategory are deliberately excluded
    # from the subcategory ranking further down, since there's nothing
    # meaningful to show in a "Top Subcategories" list for them.
    df = fetch_df(
        """
        SELECT
            e.amount,
            COALESCE(e.pay_method, 'Other') AS payment_method,
            COALESCE(a.name, 'Unknown') AS account,
            COALESCE(c.name, 'Other') AS category,
            sc.name AS subcategory
        FROM expenses e
        LEFT JOIN accounts a ON e.account_id = a.id
        LEFT JOIN categories c ON e.category_id = c.id
        LEFT JOIN subcategories sc ON e.subcategory_id = sc.id
        WHERE e.user_id = %s
        AND MONTH(e.exp_date) = %s
        AND YEAR(e.exp_date) = %s
        AND e.type = 'expense'
        """,
        (user_id, now.month, now.year)
    )

    category_totals_dict = {}
    subcategory_totals_dict = {}
    account_totals_dict = {}
    payment_totals_dict = {}
    month_amounts = {}

    if not df.empty:
        # --- CHANGED (THE ACTUAL BUG FIX): explicitly cast the amount
        # column to float right after fetching.
        #
        # Root cause of "donut always shows 0%": MySQL DECIMAL columns
        # come back from the connector as decimal.Decimal objects, so
        # `df["amount"]` was an object-dtype column of Decimals. The old
        # code did `category_totals.to_dict()` with no float cast, so
        # `| tojson` in the template had to serialize Decimal values -
        # which aren't natively JSON numbers, so they got turned into
        # *strings* (e.g. "24400.00"). In the template's JS, summing an
        # array of strings with `reduce((a,b) => a+b, 0)` does string
        # concatenation instead of addition, producing a malformed,
        # non-numeric "grand total". `grandTotal > 0` then evaluates to
        # false (NaN > 0 is false), so the ternary fallback of `0` was
        # used for every single percentage - hence "always 0%".
        #
        # Casting to float here (a real Python/numpy float, which IS a
        # JSON number) fixes this at the source for every aggregate
        # below, not just category totals.
        df["amount"] = df["amount"].astype(float)

        # Category totals (existing behavior preserved: grouped the same
        # way as before, alphabetically by category via pandas' default
        # groupby ordering) - just now sourced from the joined dataframe
        # and with the float-cast fix applied.
        category_totals_dict = df.groupby("category")["amount"].sum().to_dict()

        # --- NEW: Subcategory totals, e.g. {"Pizza": 5000.0, "Burger": 2500.0, ...}
        # Excludes rows with no subcategory (see comment on the query
        # above). Sorted descending by amount so the template can simply
        # take the first N entries for the "Top Subcategories" card
        # without needing to re-sort in JS.
        sub_df = df[df["subcategory"].notna()]
        if not sub_df.empty:
            subcategory_totals_dict = (
                sub_df.groupby("subcategory")["amount"]
                .sum()
                .sort_values(ascending=False)
                .to_dict()
            )

        # --- NEW: Account-wise totals, e.g. {"Axis Bank": 15000.0, "Cash": 5000.0, "Google Pay": 3000.0}
        # Sorted descending so the "Spending By Account" progress-bar
        # card renders biggest-spend-first, matching the example order
        # given in the requirements.
        account_totals_dict = (
            df.groupby("account")["amount"]
            .sum()
            .sort_values(ascending=False)
            .to_dict()
        )

        # --- NEW: Payment method totals, e.g. {"UPI": ..., "Cash": ..., "Debit Card": ..., "Net Banking": ...}
        # Sorted descending for the same reason as account totals above.
        payment_totals_dict = (
            df.groupby("payment_method")["amount"]
            .sum()
            .sort_values(ascending=False)
            .to_dict()
        )

    # Monthly trend (all historical expenses) - UNCHANGED.
    # This block already explicitly cast each sum to float
    # (`float(v)` below), so it was never part of the percentage bug,
    # and the requirement says the existing monthly chart should remain
    # as-is. No joins were added here since this query doesn't need
    # account/category/subcategory names - it's a pure date/amount trend.
    df_all = fetch_df(
        """
        SELECT exp_date, amount
        FROM expenses
        WHERE user_id = %s AND type = 'expense'
        """,
        (user_id,)
    )

    if not df_all.empty:
        df_all["exp_date"] = pd.to_datetime(df_all["exp_date"])
        month_amounts = (
            df_all.groupby(df_all["exp_date"].dt.month)["amount"]
            .sum().sort_index().to_dict()
        )
        month_amounts = {
            calendar.month_name[k]: float(v)
            for k, v in month_amounts.items()
        }

    # --- CHANGED: return grew from 2 values to 5 (the 3 new dicts are
    # appended after the original two, so category_totals_dict and
    # month_amounts keep their original positions). See the docstring
    # at the top of this function for the one-line change needed in the
    # calling route.
    return (
        category_totals_dict,
        month_amounts,
        subcategory_totals_dict,
        account_totals_dict,
        payment_totals_dict,
    )


def compare_months_service(user_id, month1, month2, year1, year2):
    """
    Compare daily expenses for two months.
    """
    # --- NOT CHANGED: unrelated to this request (no category/account/
    # subcategory/payment-method data involved), so left exactly as-is.
    labels = []
    m1_data = []
    m2_data = []

    if not (month1 and month2 and year1 and year2):
        return {
            "labels": labels, "m1_data": m1_data, "m2_data": m2_data,
            "month1": month1, "month2": month2, "year1": year1, "year2": year2
        }

    df = fetch_df(
        """
        SELECT exp_date, amount
        FROM expenses
        WHERE user_id = %s AND type = 'expense'
        AND (
            (MONTH(exp_date) = %s AND YEAR(exp_date) = %s)
            OR
            (MONTH(exp_date) = %s AND YEAR(exp_date) = %s)
        )
        """,
        (user_id, month1, year1, month2, year2)
    )

    if not df.empty:
        df["exp_date"] = pd.to_datetime(df["exp_date"])

        m1_df = df[(df["exp_date"].dt.month == int(month1)) & (df["exp_date"].dt.year == int(year1))]
        m2_df = df[(df["exp_date"].dt.month == int(month2)) & (df["exp_date"].dt.year == int(year2))]

        m1_group = m1_df.groupby(m1_df["exp_date"].dt.day)["amount"].sum()
        m2_group = m2_df.groupby(m2_df["exp_date"].dt.day)["amount"].sum()

        labels = list(range(1, 32))
        m1_data = [float(m1_group.get(day, 0)) for day in labels]
        m2_data = [float(m2_group.get(day, 0)) for day in labels]

    return {
        "labels": labels, "m1_data": m1_data, "m2_data": m2_data,
        "month1": month1, "month2": month2, "year1": year1, "year2": year2
    }