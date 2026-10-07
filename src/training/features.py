"""Feature engineering pipeline for XGBoost demand forecasting training and inference."""

from typing import List, Tuple
import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "day", "month", "year", "dayofweek", "weekofyear",
    "sales_mean", "sales_median", "sales_std",
    "lag_7", "lag_14", "lag_28", "lag_365"
]


def generate_training_features(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate time-based, rolling/lag, and historical statistical features for model training."""
    if df.empty:
        return pd.DataFrame(columns=FEATURE_COLUMNS + ["sales", "date", "store", "item"])

    data = df.copy()
    data["date"] = pd.to_datetime(data["date"])
    data = data.sort_values(["store", "item", "date"]).reset_index(drop=True)

    # 1. Calendar Features
    data["day"] = data["date"].dt.day
    data["month"] = data["date"].dt.month
    data["year"] = data["date"].dt.year
    data["dayofweek"] = data["date"].dt.dayofweek
    data["weekofyear"] = data["date"].dt.isocalendar().week.astype(int)

    # 2. Historical Summary Statistics per (store, item)
    stats = (
        data.groupby(["store", "item"])["sales"]
        .agg(sales_mean="mean", sales_median="median", sales_std="std")
        .reset_index()
    )
    stats["sales_std"] = stats["sales_std"].fillna(0.0)
    data = data.merge(stats, on=["store", "item"], how="left")

    # 3. Lag Features
    # Group by (store, item) to ensure lags are strictly within the same series
    for lag in [7, 14, 28, 365]:
        data[f"lag_{lag}"] = data.groupby(["store", "item"])["sales"].shift(lag)
        # Fall back to sales_mean for earliest records where lag is NaN
        data[f"lag_{lag}"] = data[f"lag_{lag}"].fillna(data["sales_mean"])

    return data


def prepare_train_validation_split(
    df: pd.DataFrame, holdout_days: int = 90
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split sales dataset temporally into train and validation sets based on holdout days."""
    df_clean = df.copy()
    df_clean["date"] = pd.to_datetime(df_clean["date"])
    max_date = df_clean["date"].max()
    split_date = max_date - pd.Timedelta(days=holdout_days)

    train_mask = df_clean["date"] <= split_date
    val_mask = df_clean["date"] > split_date

    return df_clean[train_mask].copy(), df_clean[val_mask].copy()
