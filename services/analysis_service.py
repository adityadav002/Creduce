import calendar
from datetime import datetime

import pandas as pd

from utils.dataframe_helper import fetch_df


def transaction_analysis_service(user_id):
    now = datetime.now()

    # Current month category analysis
    df = fetch_df(
        """
        SELECT exp_date, category, amount
        FROM expenses
        WHERE user_id = %s
        AND MONTH(exp_date) = %s
        AND YEAR(exp_date) = %s
        """,
        (user_id, now.month, now.year)
    )

    category_totals_dict = {}
    month_amounts = {}

    if not df.empty:
        df["exp_date"] = pd.to_datetime(df["exp_date"])

        category_totals = (
            df.groupby("category")["amount"]
            .sum()
        )

        category_totals_dict = category_totals.to_dict()

    # Monthly trend
    df_all = fetch_df(
        """
        SELECT exp_date, amount
        FROM expenses
        WHERE user_id = %s
        """,
        (user_id,)
    )

    if not df_all.empty:
        df_all["exp_date"] = pd.to_datetime(df_all["exp_date"])

        month_amounts = (
            df_all.groupby(df_all["exp_date"].dt.month)["amount"]
            .sum()
            .sort_index()
            .to_dict()
        )

        month_amounts = {
            calendar.month_name[k]: v
            for k, v in month_amounts.items()
        }

    return category_totals_dict, month_amounts


def compare_months_service(user_id, month1, month2, year1, year2):

    labels = []
    m1_data = []
    m2_data = []

    if not (month1 and month2 and year1 and year2):
        return {
            "labels": labels,
            "m1_data": m1_data,
            "m2_data": m2_data,
            "month1": month1,
            "month2": month2,
            "year1": year1,
            "year2": year2
        }

    df = fetch_df(
        """
        SELECT *
        FROM expenses
        WHERE user_id = %s
        AND (
            (MONTH(exp_date) = %s AND YEAR(exp_date) = %s)
            OR
            (MONTH(exp_date) = %s AND YEAR(exp_date) = %s)
        )
        """,
        (
            user_id,
            month1,
            year1,
            month2,
            year2
        )
    )

    if not df.empty:

        df["exp_date"] = pd.to_datetime(df["exp_date"])

        m1_df = df[
            (df["exp_date"].dt.month == int(month1))
            &
            (df["exp_date"].dt.year == int(year1))
        ]

        m2_df = df[
            (df["exp_date"].dt.month == int(month2))
            &
            (df["exp_date"].dt.year == int(year2))
        ]

        m1_group = (
            m1_df.groupby(
                m1_df["exp_date"].dt.day
            )["amount"].sum()
        )

        m2_group = (
            m2_df.groupby(
                m2_df["exp_date"].dt.day
            )["amount"].sum()
        )

        labels = list(range(1, 32))

        m1_data = [
            float(m1_group.get(day, 0))
            for day in labels
        ]

        m2_data = [
            float(m2_group.get(day, 0))
            for day in labels
        ]

    return {
        "labels": labels,
        "m1_data": m1_data,
        "m2_data": m2_data,
        "month1": month1,
        "month2": month2,
        "year1": year1,
        "year2": year2
    }