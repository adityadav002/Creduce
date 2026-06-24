from utils.db import get_cursor, close_connection
from services.prediction_service import predict_category
from services.account_service import _adjust_balance


def _get_or_create_category_id(user_id, category_name):
    if not category_name:
        return None

    category_name = category_name.strip().lower()

    cursor, db = get_cursor()
    if cursor is None:
        return None

    try:
        cursor.execute("SELECT id FROM categories WHERE user_id = %s AND LOWER(name) = %s", (user_id, category_name))
        row = cursor.fetchone()
        if row:
            return row[0]
        
        # Create it
        cursor.execute("INSERT INTO categories (user_id, name) VALUES (%s, %s)", (user_id, category_name.capitalize()))
        db.commit()
        return cursor.lastrowid
    finally:
        close_connection(cursor, db)


# --- NEW: helper to resolve a free-typed subcategory name to an id. ---
# Mirrors the existing `_get_or_create_category_id` pattern (its own
# cursor/db, its own commit) so the surrounding transaction logic in
# add_expense()/update_expense() does not need to change.
def _get_or_create_subcategory_id(user_id, category_id, subcategory_name):
    """
    Resolve a user-typed subcategory name into a subcategory_id, scoped to
    the given category_id and user_id.

    - Strips whitespace; empty/blank names resolve to None (caller keeps
      whatever subcategory_id was already selected, per requirements).
    - Looks for an existing subcategory for this user + category with a
      case-insensitive name match, and reuses its id if found, so we never
      create duplicate subcategories for the same user/category.
    - Default (built-in) subcategories have user_id = NULL and are not
      matched/reused here, since this lookup is scoped to user_id = %s
      (the current user's own subcategories) as specified.
    - If no match exists, inserts a new subcategory row owned by this user
      and returns cursor.lastrowid as the new subcategory_id.
    """
    if not category_id or not subcategory_name:
        return None

    subcategory_name = subcategory_name.strip()
    if not subcategory_name:
        return None

    cursor, db = get_cursor()
    if cursor is None:
        return None

    try:
        # Check whether this user already has a subcategory with this name
        # under the selected category, to avoid creating a duplicate.
        cursor.execute(
            """
            SELECT id
            FROM subcategories
            WHERE category_id=%s
            AND user_id=%s
            AND LOWER(name)=LOWER(%s)
            """,
            (category_id, user_id, subcategory_name)
        )
        row = cursor.fetchone()
        if row:
            return row[0]

        # Not found - create a new user-owned subcategory.
        cursor.execute(
            """
            INSERT INTO subcategories
            (category_id, user_id, name)
            VALUES (%s, %s, %s)
            """,
            (category_id, user_id, subcategory_name)
        )
        db.commit()
        return cursor.lastrowid
    finally:
        close_connection(cursor, db)


def add_expense(user_id, account_id, date, amount, note, payment, category_id_or_name, subcategory_id=None, new_subcategory=None):
    # --- NEW: `new_subcategory=None` parameter added per requirements,
    # appended after the existing `subcategory_id` parameter so all
    # existing positional/keyword callers keep working unchanged. ---
    """Add an expense using the expenses table."""
    cursor, db = get_cursor()

    if cursor is None:
        raise ConnectionError("Database connection failed")

    # Strict type casting
    account_id = int(account_id)

    try:
        db.start_transaction()

        if category_id_or_name and str(category_id_or_name).isdigit():
            category_id = int(category_id_or_name)
        else:
            resolved_category_name = (
                (category_id_or_name or "").strip().lower()
                or (predict_category(note) if note else "other")
            )
            category_id = _get_or_create_category_id(user_id, resolved_category_name)
            
        if not subcategory_id or not str(subcategory_id).isdigit():
            subcategory_id = None
        else:
            subcategory_id = int(subcategory_id)

        # --- NEW: if the caller supplied a free-typed `new_subcategory`,
        # resolve/create it (scoped to this user + the resolved
        # category_id) and let it override the selected subcategory_id.
        # If `new_subcategory` is empty/blank, nothing changes here and
        # the existing subcategory_id logic above is preserved untouched. ---
        if new_subcategory and str(new_subcategory).strip():
            resolved_subcategory_id = _get_or_create_subcategory_id(
                user_id, category_id, new_subcategory
            )
            if resolved_subcategory_id:
                subcategory_id = resolved_subcategory_id

        cursor.execute(
            """
            INSERT INTO expenses
            (user_id, account_id, category_id, subcategory_id, type, amount, pay_method, note, exp_date)
            VALUES (%s, %s, %s, %s, 'expense', %s, %s, %s, %s)
            """,
            (
                user_id,
                account_id,
                category_id,
                subcategory_id,
                amount,
                payment,
                note,
                date
            )
        )
        
        new_id = cursor.lastrowid
        
        # Adjust account balance (deduct)
        _adjust_balance(cursor, account_id, -amount, user_id)

        db.commit()
        return new_id

    except Exception:
        db.rollback()
        raise

    finally:
        close_connection(cursor, db)


def delete_expense(expense_id, user_id):
    """Delete one expense owned by the user and revert balance."""
    cursor, db = get_cursor()

    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        db.start_transaction()
        
        cursor.execute("SELECT account_id, amount FROM expenses WHERE id=%s AND user_id=%s AND type='expense'", (expense_id, user_id))
        row = cursor.fetchone()
        if not row:
            db.rollback()
            return False
            
        account_id, amount = row

        cursor.execute(
            """
            DELETE
            FROM expenses
            WHERE id=%s
            AND user_id=%s
            """,
            (expense_id, user_id)
        )

        if cursor.rowcount > 0:
            _adjust_balance(cursor, account_id, float(amount), user_id)

        db.commit()
        return cursor.rowcount > 0

    except Exception:
        db.rollback()
        raise

    finally:
        close_connection(cursor, db)


def get_expense_by_id(expense_id, user_id):
    """Fetch one expense owned by the user."""

    cursor, db = get_cursor(dictionary=True)

    if cursor is None:
        return None

    try:

        cursor.execute(
            "SELECT * FROM expenses WHERE id=%s AND user_id=%s AND type='expense'",
            (expense_id, user_id)
        )

        return cursor.fetchone()

    finally:
        close_connection(cursor, db)


def update_expense(
        expense_id,
        user_id,
        account_id,
        date,
        category_id_or_name,
        amount,
        note,
        payment,
        subcategory_id=None,
        new_subcategory=None
):
    # --- NEW: `new_subcategory=None` parameter added per requirements,
    # appended after the existing `subcategory_id` parameter so all
    # existing positional/keyword callers keep working unchanged. ---
    """Update one expense owned by the user."""

    cursor, db = get_cursor()

    if cursor is None:
        raise ConnectionError("Database connection failed")

    # Strict type casting
    account_id = int(account_id)
    amount = float(amount)

    try:
        db.start_transaction()
        
        cursor.execute("SELECT account_id, amount FROM expenses WHERE id=%s AND user_id=%s AND type='expense'", (expense_id, user_id))
        row = cursor.fetchone()
        if not row:
            db.rollback()
            return False
            
        old_account_id, old_amount = row
        
        # Revert old balance
        _adjust_balance(cursor, old_account_id, float(old_amount), user_id)
        
        if category_id_or_name and str(category_id_or_name).isdigit():
            category_id = int(category_id_or_name)
        else:
            resolved_category_name = (
                (category_id_or_name or "").strip().lower()
                or (predict_category(note) if note else "other")
            )
            category_id = _get_or_create_category_id(user_id, resolved_category_name)
            
        if not subcategory_id or not str(subcategory_id).isdigit():
            subcategory_id = None
        else:
            subcategory_id = int(subcategory_id)

        # --- NEW: same override behavior as in add_expense() - a
        # non-empty `new_subcategory` is resolved/created (scoped to this
        # user + the resolved category_id) and overrides subcategory_id.
        # An empty/blank `new_subcategory` leaves the existing behavior
        # above completely untouched. ---
        if new_subcategory and str(new_subcategory).strip():
            resolved_subcategory_id = _get_or_create_subcategory_id(
                user_id, category_id, new_subcategory
            )
            if resolved_subcategory_id:
                subcategory_id = resolved_subcategory_id

        cursor.execute(
            """
            UPDATE expenses
            SET account_id=%s,
                exp_date=%s,
                category_id=%s,
                subcategory_id=%s,
                amount=%s,
                note=%s,
                pay_method=%s
            WHERE id=%s
            AND user_id=%s
            """,
            (
                account_id,
                date,
                category_id,
                subcategory_id,
                amount,
                note,
                payment,
                expense_id,
                user_id
            )
        )

        # Apply new balance
        _adjust_balance(cursor, account_id, -amount, user_id)

        db.commit()
        return True

    except Exception:
        db.rollback()
        raise

    finally:
        close_connection(cursor, db)