"""Reproduce the Part 1 cleaning steps and export rows for Task 2 databases."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "holiday",
    "temp",
    "rain_1h",
    "snow_1h",
    "clouds_all",
    "weather_main",
    "weather_description",
    "date_time",
    "traffic_volume",
}
NUMERIC_COLUMNS = [
    "temp",
    "rain_1h",
    "snow_1h",
    "clouds_all",
    "traffic_volume",
]
CATEGORICAL_COLUMNS = [
    "holiday",
    "weather_main",
    "weather_description",
]


def prepare_data(source_path: Path, output_path: Path) -> pd.DataFrame:
    if not source_path.is_file():
        raise FileNotFoundError(f"Source CSV not found: {source_path}")

    df = pd.read_csv(source_path)
    missing_columns = REQUIRED_COLUMNS.difference(df.columns)
    if missing_columns:
        raise ValueError(
            "Source CSV is missing required column(s): "
            + ", ".join(sorted(missing_columns))
        )

    original_rows = len(df)
    df["date_time"] = pd.to_datetime(df["date_time"], errors="coerce")
    df = df.sort_values("date_time").reset_index(drop=True)

    clean_df = df.copy()
    clean_df["holiday"] = clean_df["holiday"].fillna("None")
    clean_df.loc[clean_df["rain_1h"] == 9831.3, "rain_1h"] = float("nan")

    clean_df = clean_df.groupby("date_time", as_index=False).agg(
        {
            **{column: "mean" for column in NUMERIC_COLUMNS},
            **{column: "first" for column in CATEGORICAL_COLUMNS},
        }
    )
    clean_df = clean_df.sort_values("date_time").reset_index(drop=True)
    clean_df["rain_1h"] = clean_df["rain_1h"].fillna(clean_df["rain_1h"].median())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(output_path, index=False, date_format="%Y-%m-%d %H:%M:%S")

    print(f"Source rows: {original_rows:,}")
    print(f"Rows after Part 1 timestamp aggregation: {len(clean_df):,}")
    print(f"Rows consolidated: {original_rows - len(clean_df):,}")
    print(f"Invalid timestamps dropped by groupby: {df['date_time'].isna().sum():,}")
    print(f"Remaining missing values: {int(clean_df.isna().sum().sum()):,}")
    print(f"Unique timestamps: {clean_df['date_time'].nunique():,}")
    print(f"Time range: {clean_df['date_time'].min()} to {clean_df['date_time'].max()}")
    print(f"Prepared CSV: {output_path}")

    return clean_df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply the Part 1 cleaning steps to the Metro traffic CSV."
    )
    parser.add_argument(
        "source_csv",
        nargs="?",
        type=Path,
        default=Path("data/Metro_Interstate_Traffic_Volume.csv"),
        help="Raw source CSV (default: data/Metro_Interstate_Traffic_Volume.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/cleaned_traffic.csv"),
        help="Output CSV path (default: data/cleaned_traffic.csv)",
    )
    args = parser.parse_args()
    prepare_data(args.source_csv, args.output)


if __name__ == "__main__":
    main()
