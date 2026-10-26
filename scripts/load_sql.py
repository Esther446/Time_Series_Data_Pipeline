"""Load a CSV export of the traffic dataset into the MySQL schema."""

from __future__ import annotations

import argparse
import csv
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import mysql.connector


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


def optional_text(value: str | None) -> str | None:
    if value is None or value.strip().lower() in NULL_VALUES:
        return None
    return value.strip()


def optional_decimal(value: str | None, column: str) -> Decimal | None:
    cleaned = optional_text(value)
    if cleaned is None:
        return None
    try:
        result = Decimal(cleaned)
    except InvalidOperation as error:
        raise ValueError(f"{column} must be numeric; got {value!r}") from error
    if not result.is_finite():
        raise ValueError(f"{column} must be finite; got {value!r}")
    return result


def required_integer(value: str | None, column: str) -> int:
    number = optional_decimal(value, column)
    if number is None or number != number.to_integral_value():
        raise ValueError(f"{column} must be a whole number; got {value!r}")
    return int(number)


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


def database_config() -> dict[str, Any]:
    required = ("MYSQL_USER", "MYSQL_PASSWORD")
    missing = [name for name in required if name not in os.environ]
    if missing:
        raise RuntimeError(
            "Set the MySQL environment variable(s): " + ", ".join(missing)
        )
    try:
        port = int(os.getenv("MYSQL_PORT", "3306"))
    except ValueError as error:
        raise RuntimeError("MYSQL_PORT must be an integer") from error
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": port,
        "user": os.environ["MYSQL_USER"],
        "password": os.environ["MYSQL_PASSWORD"],
        "database": os.getenv("MYSQL_DATABASE", "time_series_traffic"),
    }


def load_csv(csv_path: Path) -> int:
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    connection = mysql.connector.connect(**database_config())
    cursor = connection.cursor()
    inserted = 0
    holiday_ids: dict[str, int] = {}

    try:
        cursor.execute("SELECT 1 FROM traffic_observations LIMIT 1")
        if cursor.fetchone() is not None:
            raise RuntimeError(
                "traffic_observations is not empty. Load into a fresh schema "
                "to avoid duplicate source rows."
            )

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
                    date_time = required_timestamp(row["date_time"])
                    traffic_volume = required_integer(
                        row["traffic_volume"], "traffic_volume"
                    )
                    if traffic_volume < 0:
                        raise ValueError("traffic_volume cannot be negative")

                    holiday_name = optional_text(row["holiday"])
                    holiday_id = None
                    if holiday_name is not None:
                        if holiday_name not in holiday_ids:
                            cursor.execute(
                                "INSERT INTO holidays (holiday_name) VALUES (%s) "
                                "ON DUPLICATE KEY UPDATE "
                                "holiday_id = LAST_INSERT_ID(holiday_id)",
                                (holiday_name,),
                            )
                            holiday_ids[holiday_name] = int(cursor.lastrowid)
                        holiday_id = holiday_ids[holiday_name]

                    clouds_all = optional_decimal(row["clouds_all"], "clouds_all")
                    if clouds_all is not None and not 0 <= clouds_all <= 100:
                        raise ValueError("clouds_all must be between 0 and 100")

                    weather_values = (
                        optional_decimal(row["temp"], "temp"),
                        optional_decimal(row["rain_1h"], "rain_1h"),
                        optional_decimal(row["snow_1h"], "snow_1h"),
                        clouds_all,
                        optional_text(row["weather_main"]),
                        optional_text(row["weather_description"]),
                    )
                except (KeyError, ValueError) as error:
                    raise ValueError(f"CSV line {line_number}: {error}") from error

                cursor.execute(
                    """
                    INSERT INTO weather_observations (
                        temp, rain_1h, snow_1h, clouds_all,
                        weather_main, weather_description
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    weather_values,
                )
                weather_id = int(cursor.lastrowid)
                cursor.execute(
                    """
                    INSERT INTO traffic_observations (
                        source_row, date_time, traffic_volume, holiday_id, weather_id
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        line_number - 1,
                        date_time,
                        traffic_volume,
                        holiday_id,
                        weather_id,
                    ),
                )
                inserted += 1

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()

    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load a traffic-volume CSV into MySQL."
    )
    parser.add_argument(
        "csv_path",
        type=Path,
        help="Path to the cleaned CSV export from Part 1",
    )
    args = parser.parse_args()
    row_count = load_csv(args.csv_path)
    print(f"Committed {row_count:,} traffic observation(s) to MySQL.")


if __name__ == "__main__":
    main()
