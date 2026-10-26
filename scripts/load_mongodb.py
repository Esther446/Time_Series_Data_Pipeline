"""Upsert a CSV export of the traffic dataset into MongoDB."""

from __future__ import annotations

import argparse
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from pymongo import MongoClient, ReplaceOne


REQUIRED_COLUMNS = {
    "date_time",
    "traffic_volume",
    "holiday",
    "temp",
    "rain_1h",
    "snow_1h",
    "clouds_all",
    "weather_main",
    "weather_description",
}
NULL_VALUES = {"", "nan", "none", "null"}
BATCH_SIZE = 1000


def optional_text(value: str | None) -> str | None:
    if value is None or value.strip().lower() in NULL_VALUES:
        return None
    return value.strip()


def optional_number(value: str | None, column: str) -> int | float | None:
    cleaned = optional_text(value)
    if cleaned is None:
        return None
    try:
        number = float(cleaned)
    except ValueError as error:
        raise ValueError(f"{column} must be numeric; got {value!r}") from error
    if not (float("-inf") < number < float("inf")):
        raise ValueError(f"{column} must be finite; got {value!r}")
    if column == "clouds_all":
        if not 0 <= number <= 100:
            raise ValueError("clouds_all must be between 0 and 100")
        if number.is_integer():
            return int(number)
    return number


def required_timestamp(value: str | None) -> datetime:
    cleaned = optional_text(value)
    if cleaned is None:
        raise ValueError("date_time is required")
    try:
        result = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"date_time is not a valid ISO timestamp: {value!r}") from error
    if result.tzinfo is not None:
        raise ValueError(
            "date_time must be timezone-naive; the source dataset has no timezone"
        )
    return result


def document_from_row(row: dict[str, str], source_row: int) -> dict[str, Any]:
    try:
        traffic_text = optional_text(row["traffic_volume"])
        if traffic_text is None:
            raise ValueError("traffic_volume is required")
        traffic_value = float(traffic_text)
        if not traffic_value.is_integer() or traffic_value < 0:
            raise ValueError("traffic_volume must be a non-negative whole number")

        return {
            "_id": source_row,
            "source_row": source_row,
            "date_time": required_timestamp(row["date_time"]),
            "traffic_volume": int(traffic_value),
            "holiday": optional_text(row["holiday"]),
            "weather": {
                "temp": optional_number(row["temp"], "temp"),
                "rain_1h": optional_number(row["rain_1h"], "rain_1h"),
                "snow_1h": optional_number(row["snow_1h"], "snow_1h"),
                "clouds_all": optional_number(row["clouds_all"], "clouds_all"),
                "weather_main": optional_text(row["weather_main"]),
                "weather_description": optional_text(row["weather_description"]),
            },
        }
    except KeyError as error:
        raise ValueError(f"CSV is missing the {error.args[0]!r} column") from error


def load_csv(csv_path: Path) -> int:
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    missing_env = [
        name for name in ("MONGODB_URI",) if name not in os.environ
    ]
    if missing_env:
        raise RuntimeError(
            "Set the MongoDB environment variable(s): " + ", ".join(missing_env)
        )

    database_name = os.getenv("MONGODB_DATABASE", "time_series_traffic")
    collection_name = os.getenv(
        "MONGODB_COLLECTION", "traffic_observations"
    )
    client = MongoClient(os.environ["MONGODB_URI"])
    collection = client[database_name][collection_name]
    collection.create_index([("date_time", 1)], name="idx_date_time")

    inserted_or_updated = 0
    operations: list[ReplaceOne] = []
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames is None:
                raise ValueError("CSV file is empty or missing its header")
            missing_columns = REQUIRED_COLUMNS.difference(reader.fieldnames)
            if missing_columns:
                raise ValueError(
                    "CSV is missing required column(s): "
                    + ", ".join(sorted(missing_columns))
                )

            for line_number, row in enumerate(reader, start=2):
                try:
                    document = document_from_row(row, line_number - 1)
                except ValueError as error:
                    raise ValueError(f"CSV line {line_number}: {error}") from error
                operations.append(
                    ReplaceOne({"_id": document["_id"]}, document, upsert=True)
                )

                if len(operations) == BATCH_SIZE:
                    collection.bulk_write(operations, ordered=False)
                    inserted_or_updated += len(operations)
                    operations.clear()

        if operations:
            collection.bulk_write(operations, ordered=False)
            inserted_or_updated += len(operations)
    finally:
        client.close()

    return inserted_or_updated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upsert a traffic-volume CSV into MongoDB."
    )
    parser.add_argument(
        "csv_path",
        type=Path,
        help="Path to the cleaned CSV export from Part 1",
    )
    args = parser.parse_args()
    row_count = load_csv(args.csv_path)
    print(f"Upserted {row_count:,} traffic observation(s) into MongoDB.")


if __name__ == "__main__":
    main()
