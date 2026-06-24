from utils.db import get_cursor, close_connection


# ------------------------------------------------------------------ #
#  CATEGORIES                                                          #
# ------------------------------------------------------------------ #

def create_category(user_id: int, name: str,
                    icon: str = None, color: str = None) -> int:
    """Insert a new top-level category. Returns the new id."""
    cursor, db = get_cursor()
    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        cursor.execute(
            "INSERT INTO categories (user_id, name, icon, color) VALUES (%s, %s, %s, %s)",
            (user_id, (name or "").strip(), icon, color)
        )
        db.commit()
        return cursor.lastrowid

    except Exception:
        db.rollback()
        raise

    finally:
        close_connection(cursor, db)


def get_all_categories(user_id: int) -> list:
    """Return all categories for a user with their subcategories."""
    cursor, db = get_cursor(dictionary=True)
    if cursor is None:
        return []

    try:
        # --- CHANGED: the LEFT JOIN's ON-clause now also filters which
        # subcategories are pulled in for each category. Previously every
        # subcategory row for a category was joined in regardless of
        # owner, which meant one user's custom subcategories would leak
        # into another user's category list.
        #
        # Now a subcategory row is only joined in when:
        #   - sc.user_id IS NULL  -> it's a default/shared subcategory, or
        #   - sc.user_id = %s     -> it belongs to the current user
        #
        # Categories themselves are untouched and remain global (no
        # user_id filtering/creation here, per requirements) - only the
        # subcategory side of the join is scoped to "default OR mine".
        # The %s placeholder is bound to `user_id` via the query params
        # below; nothing else about the SELECT shape changed, so the
        # dictionary-building logic further down still works unmodified.
        cursor.execute(
            """
            SELECT
                c.id,
                c.name,
                c.icon,
                c.color,
                sc.id AS sub_id,
                sc.name AS sub_name
            FROM categories c
            LEFT JOIN subcategories sc
                ON sc.category_id = c.id
                AND (
                    sc.user_id IS NULL
                    OR sc.user_id = %s
                )
            ORDER BY c.name, sc.name
            """,
            (user_id,)
        )
        rows = cursor.fetchall()

        # Collapse into {category: [subcategories]} structure
        # (unchanged - still keyed/built exactly as before)
        categories: dict = {}
        for row in rows:
            cat_id = row['id']
            if cat_id not in categories:
                categories[cat_id] = {
                    "id": cat_id, "name": row['name'],
                    "icon": row.get('icon'), "color": row.get('color'),
                    "subcategories": [],
                }
            if row.get('sub_id'):
                categories[cat_id]["subcategories"].append(
                    {"id": row['sub_id'], "name": row['sub_name']}
                )

        return list(categories.values())

    finally:
        close_connection(cursor, db)


def update_category(category_id: int, user_id: int, name: str,
                    icon: str = None, color: str = None) -> bool:
    """Rename / recolor a category. Returns True if updated."""
    cursor, db = get_cursor()
    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        cursor.execute(
            """
            UPDATE categories
            SET name = %s, icon = %s, color = %s
            WHERE id = %s AND user_id = %s
            """,
            (name, icon, color, category_id, user_id)
        )
        db.commit()
        return cursor.rowcount > 0

    except Exception:
        db.rollback()
        raise

    finally:
        close_connection(cursor, db)


def delete_category(category_id: int, user_id: int) -> bool:
    """
    Delete a category and cascade-delete its subcategories.
    Transactions referencing this category will have category_id set to NULL.
    Returns True if deleted.
    """
    cursor, db = get_cursor()
    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        cursor.execute(
            "DELETE FROM categories WHERE id = %s AND user_id = %s",
            (category_id, user_id)
        )
        db.commit()
        return cursor.rowcount > 0

    except Exception:
        db.rollback()
        raise

    finally:
        close_connection(cursor, db)


# ------------------------------------------------------------------ #
#  SUBCATEGORIES                                                       #
# ------------------------------------------------------------------ #

def create_subcategory(category_id: int, name: str) -> int:
    """Add a subcategory under an existing category. Returns the new id."""
    cursor, db = get_cursor()
    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        cursor.execute(
            "INSERT INTO subcategories (category_id, name) VALUES (%s, %s)",
            (category_id, (name or "").strip())
        )
        db.commit()
        return cursor.lastrowid

    except Exception:
        db.rollback()
        raise

    finally:
        close_connection(cursor, db)


def rename_subcategory(subcategory_id: int, name: str) -> bool:
    """Rename a subcategory. Returns True if updated."""
    cursor, db = get_cursor()
    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        cursor.execute(
            "UPDATE subcategories SET name = %s WHERE id = %s",
            ((name or "").strip(), subcategory_id)
        )
        db.commit()
        return cursor.rowcount > 0

    except Exception:
        db.rollback()
        raise

    finally:
        close_connection(cursor, db)


def delete_subcategory(subcategory_id: int) -> bool:
    """
    Delete a subcategory.
    Transactions referencing it will have subcategory_id set to NULL.
    Returns True if deleted.
    """
    cursor, db = get_cursor()
    if cursor is None:
        raise ConnectionError("Database connection failed")

    try:
        cursor.execute(
            "DELETE FROM subcategories WHERE id = %s",
            (subcategory_id,)
        )
        db.commit()
        return cursor.rowcount > 0

    except Exception:
        db.rollback()
        raise

    finally:
        close_connection(cursor, db)