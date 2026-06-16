import pandas as pd
from utils.db import get_cursor, close_connection


def fetch_df(query, params=None):
    """Execute query and return DataFrame"""
    cursor, db = get_cursor()
    if cursor is None:
        return pd.DataFrame()

    try:
        cursor.execute(query, params or ())
        data = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        return pd.DataFrame(data, columns=columns)
    finally:
        close_connection(cursor, db)