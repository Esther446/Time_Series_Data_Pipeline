"""Train the Part 1 Random Forest and save it for the Task 4 prediction script.

The notebook trains the model but never saves it. This script repeats the same
feature engineering, chronological 70/15/15 split and hyperparameters, then
writes the fitted model to models/random_forest.joblib.

Run prepare_data.py first so data/cleaned_traffic.csv exists.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

PROJECT_ROOT = Path(__file__).resolve().parent.parent

FEATURE_COLUMNS = [
    "hour",
    "day_of_week",
    "month",
    "traffic_lag_1",
    "traffic_lag_24",
    "traffic_ma_24",
]
TARGET_COLUMN = "traffic_volume"


def build_training_data(cleaned_csv: Path) -> pd.DataFrame:
    """Create the same features as the Part 1 notebook."""
    df = pd.read_csv(cleaned_csv, parse_dates=["date_time"])
    df = df[["date_time", "traffic_volume"]].sort_values("date_time").reset_index(drop=True)

    df["hour"] = df["date_time"].dt.hour
    df["day_of_week"] = df["date_time"].dt.day_of_week
    df["month"] = df["date_time"].dt.month
    df["traffic_lag_1"] = df["traffic_volume"].shift(1)
    df["traffic_lag_24"] = df["traffic_volume"].shift(24)
    # shift(1) so the average only uses past observations
    df["traffic_ma_24"] = df["traffic_volume"].shift(1).rolling(24).mean()

    return df.dropna().reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and save the Random Forest model.")
    parser.add_argument(
        "--data",
        type=Path,
        default=PROJECT_ROOT / "data" / "cleaned_traffic.csv",
        help="Cleaned CSV written by prepare_data.py",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "models" / "random_forest.joblib",
        help="Where to save the trained model",
    )
    args = parser.parse_args()

    model_df = build_training_data(args.data)

    # Chronological split: 70% train, 15% validation, 15% test
    n = len(model_df)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    train_df = model_df.iloc[:train_end]
    test_df = model_df.iloc[val_end:]

    # Best settings from the validation tuning in the notebook
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=20,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(train_df[FEATURE_COLUMNS], train_df[TARGET_COLUMN])

    test_pred = model.predict(test_df[FEATURE_COLUMNS])
    y_test = test_df[TARGET_COLUMN]
    print(f"Training rows: {len(train_df):,}   Test rows: {len(test_df):,}")
    print(f"Test MAE:  {mean_absolute_error(y_test, test_pred):.2f}")
    print(f"Test RMSE: {np.sqrt(mean_squared_error(y_test, test_pred)):.2f}")
    print(f"Test R2:   {r2_score(y_test, test_pred):.4f}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, args.output, compress=3)
    print(f"Model saved to: {args.output}")


if __name__ == "__main__":
    main()
