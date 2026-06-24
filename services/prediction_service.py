import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from utils.model_loader import model


def predict_category(note):
    """
    Predict expense category from a text note using the
    pre-trained ML model.
    """
    cleaned_note = (note or "").strip()
    if not cleaned_note:
        return "other"

    try:
        return str(model.predict([cleaned_note])[0]).lower()
    except Exception as exc:
        print(f"CATEGORY PREDICTION ERROR: {exc}")
        return "other"


def predict_monthly_expense(df):
    """
    Predict next month's total expense using LinearRegression.

    Excludes:
    - current month
    - income transactions
    - future transfer transactions

    Args:
        df : DataFrame containing expenses data

    Returns:
        int
    """

    if df.empty:
        return 0

    pred_df = df.copy()

    # Keep only expense transactions
    if "type" in pred_df.columns:
        pred_df = pred_df[
            pred_df["type"] == "expense"
        ]

    if pred_df.empty:
        return 0

    pred_df["exp_date"] = pd.to_datetime(
        pred_df["exp_date"]
    )

    pred_df["amount"] = (
        pred_df["amount"]
        .astype(str)
        .str.replace("₹", "", regex=False)
        .str.replace(",", "", regex=False)
        .astype(float)
    )

    monthly_pred = (
        pred_df
        .resample(
            "ME",
            on="exp_date"
        )["amount"]
        .sum()
        .reset_index()
    )

    current_month = pd.Timestamp.now().month
    current_year = pd.Timestamp.now().year

    # Remove current (incomplete) month
    monthly_pred = monthly_pred[
        ~(
            (monthly_pred["exp_date"].dt.month == current_month)
            &
            (monthly_pred["exp_date"].dt.year == current_year)
        )
    ]

    if len(monthly_pred) < 2:
        return 0

    monthly_pred["t"] = range(
        len(monthly_pred)
    )

    reg = LinearRegression()

    reg.fit(
        monthly_pred[["t"]],
        monthly_pred["amount"]
    )

    next_t = np.array(
        [[monthly_pred["t"].max() + 1]]
    )

    predicted_expense = int(
        reg.predict(next_t)[0]
    )

    return max(predicted_expense, 0)
