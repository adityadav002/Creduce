import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from utils.model_loader import model


def predict_category(note):
    """
    Predict expense category from a text note using the pre-trained ML model.
    Moved from app.py /addExpense handler.
    """
    return model.predict([note])[0]


def predict_monthly_expense(df):
    """
    Predict next month's total expense using LinearRegression on historical monthly totals.
    Excludes the current (incomplete) month from training data.
    Moved from app.py main() prediction block.

    Args:
        df: Full expenses DataFrame with exp_date and amount columns.

    Returns:
        int: Predicted expense for next month, or 0 if insufficient data.
    """
    pred_df = df.copy()
    pred_df["exp_date"] = pd.to_datetime(pred_df["exp_date"])

    pred_df["amount"] = (
        pred_df["amount"]
        .astype(str)
        .str.replace("₹", "", regex=False)
        .str.replace(",", "", regex=False)
        .astype(float)
    )

    monthly_pred = pred_df.resample("ME", on="exp_date")["amount"].sum().reset_index()

    current_month = pd.Timestamp.now().month
    current_year = pd.Timestamp.now().year

    # Exclude current (incomplete) month
    monthly_pred = monthly_pred[
        ~(
            (monthly_pred["exp_date"].dt.month == current_month) &
            (monthly_pred["exp_date"].dt.year == current_year)
        )
    ]

    monthly_pred["t"] = range(len(monthly_pred))

    if len(monthly_pred) >= 2:
        reg = LinearRegression()
        reg.fit(monthly_pred[["t"]], monthly_pred["amount"])

        next_t = np.array([[monthly_pred["t"].max() + 1]])
        predicted_expense = int(reg.predict(next_t)[0])

        print("MONTHLY PRED DATA:")
        print(monthly_pred)

        return predicted_expense

    return 0