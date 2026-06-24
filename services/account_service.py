from utils.db import get_cursor, close_connection


# ------------------------------------------------------------------ #
#  CREATE                                                              #
# ------------------------------------------------------------------ #

def create_account(user_id: int, name: str, account_type: str,
                   initial_balance: float = 0.0,
                   icon: str = None, color: str = None) -> int:
    """
    Insert a new account. current_balance starts equal to initial_balance.
    Returns the new account id.
    """
    cursor, db = get_cursor()
    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        cursor.execute(
            """
            INSERT INTO accounts
                (user_id, name, type, initial_balance, current_balance, icon, color)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, name, account_type, initial_balance, initial_balance, icon, color)
        )
        db.commit()
        return cursor.lastrowid

    except Exception:
        db.rollback()
        raise

    finally:
        close_connection(cursor, db)


# ------------------------------------------------------------------ #
#  READ                                                                #
# ------------------------------------------------------------------ #

def get_account(account_id: int, user_id: int) -> tuple | None:
    """Fetch a single account row scoped to the user."""
    cursor, db = get_cursor()
    if cursor is None:
        return None

    try:
        cursor.execute(
            "SELECT * FROM accounts WHERE id = %s AND user_id = %s",
            (account_id, user_id)
        )
        return cursor.fetchone()

    finally:
        close_connection(cursor, db)


def get_all_accounts(user_id: int) -> list:
    """Return all accounts for a user as dictionaries."""
    cursor, db = get_cursor(dictionary=True)
    if cursor is None:
        return []

    try:
        cursor.execute("SELECT * FROM accounts ORDER BY name ASC")
        return cursor.fetchall()

    finally:
        close_connection(cursor, db)


def get_total_balance(user_id: int) -> float:
    """Sum current_balance across all accounts for the user."""
    cursor, db = get_cursor()
    if cursor is None:
        return 0.0

    try:
        cursor.execute(
            "SELECT COALESCE(SUM(current_balance), 0) FROM accounts WHERE user_id = %s",
            (user_id,)
        )
        row = cursor.fetchone()
        return float(row[0]) if row else 0.0

    finally:
        close_connection(cursor, db)


# ------------------------------------------------------------------ #
#  UPDATE                                                              #
# ------------------------------------------------------------------ #

def update_account(account_id: int, user_id: int, name: str,
                   account_type: str, icon: str = None, color: str = None) -> bool:
    """Update account metadata (not balance — balances are managed by transactions)."""
    cursor, db = get_cursor()
    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        cursor.execute(
            """
            UPDATE accounts
            SET name = %s, type = %s, icon = %s, color = %s
            WHERE id = %s AND user_id = %s
            """,
            (name, account_type, icon, color, account_id, user_id)
        )
        db.commit()
        return cursor.rowcount > 0

    except Exception:
        db.rollback()
        raise

    finally:
        close_connection(cursor, db)


def _adjust_balance(cursor, account_id: int, delta: float, user_id: int | None = None):
    """
    Internal helper — add delta (positive or negative) to current_balance.
    Must be called inside an open transaction; does NOT commit.
    """
    if user_id is None:
        cursor.execute(
            "UPDATE accounts SET current_balance = current_balance + %s WHERE id = %s",
            (delta, account_id)
        )
    else:
        cursor.execute(
            "UPDATE accounts SET current_balance = current_balance + %s WHERE id = %s AND user_id = %s",
            (delta, account_id, user_id)
        )
    if cursor.rowcount == 0:
        raise ValueError("Account not found")


# ------------------------------------------------------------------ #
#  DELETE                                                              #
# ------------------------------------------------------------------ #

def delete_account(account_id: int, user_id: int) -> bool:
    """
    Delete an account and cascade-delete its transactions (via FK).
    Returns True if a row was deleted.
    """
    cursor, db = get_cursor()
    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        cursor.execute(
            "DELETE FROM accounts WHERE id = %s AND user_id = %s",
            (account_id, user_id)
        )
        db.commit()
        return cursor.rowcount > 0

    except Exception:
        db.rollback()
        raise

    finally:
        close_connection(cursor, db)


# ------------------------------------------------------------------ #
#  TRANSACTION MANAGEMENT (income / expense / transfer)               #
# ------------------------------------------------------------------ #

def add_transaction(user_id: int, account_id: int, category_id: int | None,
                    subcategory_id: int | None, txn_type: str, amount: float,
                    payment_method: str, notes: str, transaction_date: str) -> int:
    """
    Insert a transaction and update the account balance atomically.
    - income  → +amount
    - expense → -amount
    - transfer → handled separately via create_transfer()
    Returns the new transaction id.
    """
    if txn_type not in ("income", "expense"):
        raise ValueError("Use create_transfer() for transfers.")

    cursor, db = get_cursor()
    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        db.start_transaction()

        cursor.execute(
            """
            INSERT INTO expenses
                (user_id, account_id, category_id, subcategory_id, type,
                 amount, pay_method, note, exp_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, account_id, category_id, subcategory_id, txn_type,
             amount, payment_method, notes, transaction_date)
        )
        new_id = cursor.lastrowid

        delta = amount if txn_type == "income" else -amount
        _adjust_balance(cursor, account_id, delta, user_id)

        db.commit()
        return new_id

    except Exception:
        db.rollback()
        raise

    finally:
        close_connection(cursor, db)


def update_transaction(txn_id: int, user_id: int, account_id: int,
                       category_id: int | None, subcategory_id: int | None,
                       txn_type: str, amount: float, payment_method: str,
                       notes: str, transaction_date: str) -> bool:
    """
    Update a transaction and recalculate account balance atomically.
    Reverses the old amount, then applies the new amount.
    """
    cursor, db = get_cursor()
    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        db.start_transaction()

        # Fetch old values to reverse balance effect
        cursor.execute(
            "SELECT account_id, type, amount FROM expenses WHERE id = %s AND user_id = %s",
            (txn_id, user_id)
        )
        old = cursor.fetchone()
        if not old:
            db.rollback()
            return False

        old_account_id, old_type, old_amount = old

        # Reverse old balance effect
        old_delta = float(old_amount) if old_type == "income" else -float(old_amount)
        _adjust_balance(cursor, old_account_id, -old_delta, user_id)

        # Apply new values
        cursor.execute(
            """
            UPDATE expenses
            SET account_id = %s, category_id = %s, subcategory_id = %s,
                type = %s, amount = %s, pay_method = %s,
                note = %s, exp_date = %s
            WHERE id = %s AND user_id = %s
            """,
            (account_id, category_id, subcategory_id, txn_type,
             amount, payment_method, notes, transaction_date, txn_id, user_id)
        )

        new_delta = amount if txn_type == "income" else -amount
        _adjust_balance(cursor, account_id, new_delta, user_id)

        db.commit()
        return True

    except Exception:
        db.rollback()
        raise

    finally:
        close_connection(cursor, db)


def delete_transaction(txn_id: int, user_id: int) -> bool:
    """Delete a transaction and reverse its balance effect atomically."""
    cursor, db = get_cursor()
    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        db.start_transaction()

        cursor.execute(
            "SELECT account_id, type, amount FROM expenses WHERE id = %s AND user_id = %s",
            (txn_id, user_id)
        )
        row = cursor.fetchone()
        if not row:
            db.rollback()
            return False

        account_id, txn_type, amount = row

        cursor.execute(
            "DELETE FROM expenses WHERE id = %s AND user_id = %s",
            (txn_id, user_id)
        )

        delta = float(amount) if txn_type == "income" else -float(amount)
        _adjust_balance(cursor, account_id, -delta, user_id)

        db.commit()
        return True

    except Exception:
        db.rollback()
        raise

    finally:
        close_connection(cursor, db)


def get_transaction_history_v2(user_id: int, account_id: int | None = None,
                                limit: int = 50) -> list:
    """
    Return recent transactions with joined account/category names.
    Optionally filtered by account. Excludes transfers.
    """
    cursor, db = get_cursor()
    if cursor is None:
        return []

    try:
        query = """
            SELECT
                t.id,
                t.exp_date AS transaction_date,
                t.amount,
                t.type,
                t.pay_method AS payment_method,
                t.note AS notes,
                a.name  AS account_name,
                c.name  AS category_name,
                sc.name AS subcategory_name
            FROM expenses t
            JOIN accounts     a  ON a.id  = t.account_id
            LEFT JOIN categories   c  ON c.id  = t.category_id
            LEFT JOIN subcategories sc ON sc.id = t.subcategory_id
            WHERE t.user_id = %s AND t.type != 'transfer'
        """
        params = [user_id]

        if account_id:
            query += " AND t.account_id = %s"
            params.append(account_id)

        query += " ORDER BY t.exp_date DESC, t.id DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, tuple(params))
        return cursor.fetchall()

    finally:
        close_connection(cursor, db)


# ------------------------------------------------------------------ #
#  TRANSFER                                                            #
# ------------------------------------------------------------------ #

def create_transfer(user_id: int, from_account_id: int, to_account_id: int,
                    amount: float, notes: str, transfer_date: str) -> int:
    """
    Move money between two accounts atomically.
    Inserts into transfers table only — not transactions — so it is
    excluded from all category/analytics queries.
    Returns the new transfer id.
    """
    cursor, db = get_cursor()
    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        db.start_transaction()

        cursor.execute(
            """
            SELECT id, current_balance
            FROM accounts
            WHERE id IN (%s, %s) AND user_id = %s
            """,
            (from_account_id, to_account_id, user_id)
        )
        accounts = {row[0]: float(row[1]) for row in cursor.fetchall()}
        if from_account_id not in accounts or to_account_id not in accounts:
            raise ValueError("Both accounts must belong to the current user")
        if accounts[from_account_id] < amount:
            raise ValueError("Insufficient funds in source account")

        cursor.execute(
            """
            INSERT INTO transfers
                (user_id, from_account_id, to_account_id, amount, note, transfer_date)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, from_account_id, to_account_id, amount, notes, transfer_date)
        )
        new_id = cursor.lastrowid

        _adjust_balance(cursor, from_account_id, -amount, user_id)
        _adjust_balance(cursor, to_account_id, amount, user_id)

        db.commit()
        return new_id

    except Exception:
        db.rollback()
        raise

    finally:
        close_connection(cursor, db)


# ------------------------------------------------------------------ #
#  REPORTS                                                             #
# ------------------------------------------------------------------ #

def get_spending_by_category(user_id: int, account_id: int | None = None,
                              start_date: str = None, end_date: str = None) -> list:
    """
    Spending totals grouped by category.
    Filters: account, date range. Excludes income and transfers.
    """
    cursor, db = get_cursor()
    if cursor is None:
        return []

    try:
        query = """
            SELECT
                COALESCE(c.name, 'Uncategorised') AS category,
                SUM(t.amount) AS total
            FROM expenses t
            LEFT JOIN categories c ON c.id = t.category_id
            WHERE t.user_id = %s AND t.type = 'expense'
        """
        params = [user_id]

        if account_id:
            query += " AND t.account_id = %s"
            params.append(account_id)
        if start_date:
            query += " AND t.exp_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND t.exp_date <= %s"
            params.append(end_date)

        query += " GROUP BY c.id, c.name ORDER BY total DESC"

        cursor.execute(query, tuple(params))
        return cursor.fetchall()

    finally:
        close_connection(cursor, db)


def get_spending_by_account(user_id: int, start_date: str = None,
                             end_date: str = None) -> list:
    """
    Spending totals grouped by account.
    Excludes income and transfers.
    """
    cursor, db = get_cursor()
    if cursor is None:
        return []

    try:
        query = """
            SELECT
                a.name       AS account_name,
                SUM(t.amount) AS total
            FROM expenses t
            JOIN accounts a ON a.id = t.account_id
            WHERE t.user_id = %s AND t.type = 'expense'
        """
        params = [user_id]

        if start_date:
            query += " AND t.exp_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND t.exp_date <= %s"
            params.append(end_date)

        query += " GROUP BY a.id, a.name ORDER BY total DESC"

        cursor.execute(query, tuple(params))
        return cursor.fetchall()

    finally:
        close_connection(cursor, db)
