import pandas as pd
from datetime import datetime
from utils.db import get_cursor, close_connection
from utils.dataframe_helper import fetch_df

def get_transaction_history(user_id):
    """
    Fetch all transactions for a user ordered by date descending.
    """
    # --- NOT CHANGED: this still feeds templates/transaction_detail.html,
    # which is outside the scope of this request and still expects plain
    # positional tuples in this exact column order. Left untouched.

    cursor, db = get_cursor()
    if cursor is None:
        return []

    try:
        cursor.execute(
            """
            SELECT e.id, e.exp_date, a.name AS account_name, c.name AS category_name,
                   sc.name AS subcategory_name, e.amount, e.note, e.pay_method
            FROM expenses e
            LEFT JOIN accounts a ON e.account_id = a.id
            LEFT JOIN categories c ON e.category_id = c.id
            LEFT JOIN subcategories sc ON e.subcategory_id = sc.id
            WHERE e.user_id = %s AND e.type = 'expense'
            ORDER BY e.exp_date DESC, e.id DESC
            """,
            (user_id,)
        )

        return cursor.fetchall()

    finally:
        close_connection(cursor, db)


def filter_transactions(
    user_id,
    category=None,
    subcategory=None,
    account=None,
    payment=None,
    month=None,
    search=None,
    date_from=None,
    date_to=None
):
    """
    Filter transactions by category, subcategory, account, payment
    method, month, a free-text search term, and/or a date range.

    --- CHANGED (root cause of the page crash + the requested rewrite):
    1. Switched to a *dictionary* cursor (`get_cursor(dictionary=True)`),
       so every row is a dict like:
           {
               "id": ..., "exp_date": ..., "account_name": ...,
               "category_name": ..., "subcategory_name": ...,
               "amount": ..., "note": ..., "pay_method": ...
           }
       instead of a positional tuple. The old template indexed into the
       tuple with row[3] assuming "amount", but the query's column order
       had changed (row[3] is now category_name, a string) - that
       mismatch is exactly what produced
       `TypeError: unsupported operand type(s) for +: 'int' and 'str'`
       when the template tried to sum amounts. Returning dicts removes
       the index-guessing entirely: the template now reads row.amount /
       row["amount"] by name, so this class of bug can't happen again
       even if column order changes later.
    2. Added 5 new optional filter parameters (subcategory, account,
       search, date_from, date_to) per the Phase 2 requirements, on top
       of the existing category/month/payment. All are optional and
       default to None so existing call sites that only pass the
       original 3 keyword args keep working.
    """
    cursor, db = get_cursor(dictionary=True)

    if cursor is None:
        return []

    try:
        # --- CHANGED: this guard now checks all 8 possible filters
        # instead of just the original 3. Behavior is otherwise
        # unchanged - if literally nothing was submitted, return an
        # empty list so the page shows its "no results yet" empty
        # state instead of dumping the user's entire history.
        if not any([category, subcategory, account, payment, month, search, date_from, date_to]):
            return []

        # --- CHANGED: query now joins `accounts` and `subcategories` in
        # addition to the existing `categories` join, and selects the
        # same 8 named columns get_transaction_history() already uses,
        # so both functions hand back data shaped the same way.
        # COALESCE on account/category gives a sane fallback label if a
        # transaction's account or category was somehow deleted/missing;
        # subcategory_name is intentionally left NULL-able since the
        # template is responsible for rendering "—" when it's absent.
        query = """
        SELECT
            e.id,
            e.exp_date,
            COALESCE(a.name, 'Unknown') AS account_name,
            COALESCE(c.name, 'Other') AS category_name,
            sc.name AS subcategory_name,
            e.amount,
            e.note,
            e.pay_method
        FROM expenses e
        LEFT JOIN accounts a ON e.account_id = a.id
        LEFT JOIN categories c ON e.category_id = c.id
        LEFT JOIN subcategories sc ON e.subcategory_id = sc.id
        WHERE e.user_id = %s AND e.type = 'expense'
        """

        params = [user_id]

        # Existing filters - logic/behavior unchanged from before.
        if category and category != "all":
            query += " AND c.name = %s"
            params.append(category)

        if payment and payment != "all":
            query += " AND e.pay_method = %s"
            params.append(payment)

        if month and month != "all":
            query += " AND MONTH(e.exp_date) = %s"
            params.append(int(month))

        # --- NEW: Subcategory filter. Matches against the subcategory
        # actually linked to each expense (via the LEFT JOIN above), so
        # this is always scoped correctly even though subcategory names
        # aren't globally unique across categories.
        if subcategory and subcategory != "all":
            query += " AND sc.name = %s"
            params.append(subcategory)

        # --- NEW: Account filter.
        if account and account != "all":
            query += " AND a.name = %s"
            params.append(account)

        # --- NEW: Date range filter. Both ends are optional and can be
        # used independently (e.g. only "From" with no "To").
        if date_from:
            query += " AND e.exp_date >= %s"
            params.append(date_from)

        if date_to:
            query += " AND e.exp_date <= %s"
            params.append(date_to)

        # --- NEW: Free-text search across note, category, subcategory,
        # and account - per the requirement "Search across: note,
        # category, subcategory, account".
        if search:
            query += """
            AND (
                e.note LIKE %s
                OR c.name LIKE %s
                OR sc.name LIKE %s
                OR a.name LIKE %s
            )
            """
            like_term = f"%{search}%"
            params.extend([like_term, like_term, like_term, like_term])

        query += " ORDER BY e.exp_date DESC, e.id DESC"

        cursor.execute(query, tuple(params))

        return cursor.fetchall()

    finally:
        close_connection(cursor, db)


def get_user_accounts(user_id):
    """
    --- NEW: helper added to populate the Account filter dropdown on the
    Filter Transactions page. Returns the distinct accounts this user
    has actually recorded expenses against, e.g.:
        [{"id": 1, "name": "Axis Bank"}, {"id": 2, "name": "Cash"}, ...]
    Scoped to the user's own expenses (via the join) rather than
    listing every account in the table, since the `accounts` table
    itself has no user_id column to filter on directly.
    """
    cursor, db = get_cursor(dictionary=True)

    if cursor is None:
        return []

    try:
        cursor.execute(
            """
            SELECT DISTINCT a.id, a.name
            FROM expenses e
            JOIN accounts a ON e.account_id = a.id
            WHERE e.user_id = %s AND e.type = 'expense'
            ORDER BY a.name
            """,
            (user_id,)
        )
        return cursor.fetchall()
    finally:
        close_connection(cursor, db)


def monthly_transaction_details(user_id):
    """
    Return a dictionary:
    {
        category_name: [
            {
                amount,
                note,
                pay_method,
                exp_date,
                account,
                subcategory
            }
        ]
    }

    for the current month.
    """
    # --- NOT CHANGED: this function (and the query/columns it uses) is
    # unrelated to the Filter Transactions page covered by this request,
    # so it's left exactly as provided.

    now = datetime.now()
    df = fetch_df(
        """
        SELECT
            e.amount,
            e.note,
            e.pay_method,
            e.exp_date,
            COALESCE(c.name, 'Other') AS category,
            COALESCE(a.name, 'Unknown') AS account,
            sc.name AS subcategory
        FROM expenses e
        LEFT JOIN categories c
            ON e.category_id = c.id
        LEFT JOIN accounts a
            ON e.account_id = a.id
        LEFT JOIN subcategories sc
            ON e.subcategory_id = sc.id
        WHERE e.user_id = %s
        AND e.type = 'expense'
        """,
        (user_id,)
    )

    if df.empty:
        return {}

    df["exp_date"] = pd.to_datetime(df["exp_date"])

    monthly_df = df[
        (df["exp_date"].dt.month == now.month)
        &
        (df["exp_date"].dt.year == now.year)
    ]

    if monthly_df.empty:
        return {}

    category_details = (
        monthly_df
        .groupby("category")
        .apply(
            lambda x: x[
            [
                "amount",
                "note",
                "pay_method",
                "exp_date",
                "account",
                "subcategory"
            ]
        ].to_dict("records")
        )
        .to_dict()
    )

    return category_details