"""Task 4: forecast the next traffic volume from data served by the API.

Steps
1. Fetch the most recent observations from the API (MySQL or MongoDB endpoint).
2. Rebuild the Part 1 features: hour, day of week, month, lag-1, lag-24 and
   the 24-observation moving average.
3. Load the trained Random Forest.
4. Predict the traffic volume of the next observation.

Example:
    python scripts/predict.py --database mongodb
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx
import joblib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "random_forest.joblib"

ENDPOINTS = {
    "sql": "/api/sql/records/recent",
    "mongodb": "/api/mongodb/records/recent",
}

# Same columns, in the same order, as the notebook used to train the model.
FEATURE_COLUMNS = [
    "hour",
    "day_of_week",
    "month",
    "traffic_lag_1",
    "traffic_lag_24",
    "traffic_ma_24",
]

# lag-24 and the 24-observation moving average both need the last 24 rows.
WINDOW = 24


def fetch_recent_records(base_url: str, database: str, limit: int = WINDOW) -> list[dict]:
    """Ask the API for the newest `limit` observations."""
    url = base_url.rstrip("/") + ENDPOINTS[database]
    try:
        response = httpx.get(url, params={"limit": limit}, timeout=30)
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise RuntimeError(
            f"API returned {error.response.status_code}: {error.response.text}"
        ) from error
    except httpx.RequestError as error:
        raise RuntimeError(f"Could not reach the API at {url}: {error}") from error
    return response.json()


def to_history_frame(records: list[dict]) -> pd.DataFrame:
    """Turn the API records into a clean, oldest-first series."""
    if not records:
        raise ValueError("The API returned no records.")

    df = pd.DataFrame(records)[["date_time", "traffic_volume"]]
    df["date_time"] = pd.to_datetime(df["date_time"])
    df["traffic_volume"] = pd.to_numeric(df["traffic_volume"])

    if df["traffic_volume"].isna().any():
        raise ValueError("Some records have no traffic_volume.")

    # Part 1 rule: one row per timestamp, duplicates averaged.
    # groupby also puts the rows in chronological order (the API sends newest first).
    return df.groupby("date_time", as_index=False)["traffic_volume"].mean()


def build_features(history: pd.DataFrame, target_time: pd.Timestamp | None = None):
    """Build the one-row feature table for the observation after the last one."""
    if len(history) < WINDOW:
        raise ValueError(f"Need at least {WINDOW} observations, got {len(history)}.")

    window = history.tail(WINDOW)
    volumes = window["traffic_volume"].to_numpy()
    latest_time = window["date_time"].iloc[-1]

    if target_time is None:
        target_time = latest_time + pd.Timedelta(hours=1)
    elif target_time <= latest_time:
        raise ValueError(f"target time {target_time} is not after the latest record {latest_time}.")

    features = pd.DataFrame(
        [
            {
                "hour": target_time.hour,
                "day_of_week": target_time.day_of_week,
                "month": target_time.month,
                "traffic_lag_1": volumes[-1],  # most recent observation
                "traffic_lag_24": volumes[0],  # 24 observations before the target
                "traffic_ma_24": volumes.mean(),  # mean of the last 24 observations
            }
        ],
        columns=FEATURE_COLUMNS,
    )
    return features, target_time


def load_model(model_path: Path):
    if not model_path.is_file():
        raise FileNotFoundError(
            f"Model file not found: {model_path}\nRun scripts/train_model.py to create it."
        )
    return joblib.load(model_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Forecast the next traffic volume.")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000", help="Base URL of the API")
    parser.add_argument(
        "--database",
        choices=ENDPOINTS,
        default="sql",
        help="Which database endpoint to read from (default: sql)",
    )
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument(
        "--target-time",
        help="Timestamp to forecast, e.g. '2018-10-01 08:00'. Default: one hour after the latest record.",
    )
    args = parser.parse_args()

    try:
        # 1. Fetch
        records = fetch_recent_records(args.api_url, args.database)

        # 2. Preprocess
        history = to_history_frame(records)
        target_time = pd.Timestamp(args.target_time) if args.target_time else None
        features, target_time = build_features(history, target_time)

        # 3. Load the trained model
        model = load_model(args.model_path)
    except (RuntimeError, ValueError, FileNotFoundError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    # 4. Predict
    prediction = float(model.predict(features)[0])

    window = history.tail(WINDOW)
    first_time, last_time = window["date_time"].iloc[0], window["date_time"].iloc[-1]
    print(f"Source: {args.database} endpoint at {args.api_url}")
    print(f"Observations used: {len(window)} ({first_time} to {last_time})")
    if last_time - first_time != pd.Timedelta(hours=WINDOW - 1):
        # The dataset has gaps, so the lags are "previous observations", not exact hours.
        print("Note: these observations are not exactly one hour apart.")
    print(f"Latest traffic volume: {window['traffic_volume'].iloc[-1]:.0f}")
    print(f"Forecast for: {target_time}")
    print(features.round(2).to_string(index=False))
    print(f"Predicted traffic volume: {prediction:.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
