"""Run Task 2 query equivalents against the Part 1 prepared CSV.

This is a local reproducibility check for query outputs. It does not replace
running sql/queries.sql against MySQL or mongodb/queries.js against MongoDB.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd


SQL_SETUP = """
CREATE TABLE holidays (
    holiday_id INTEGER PRIMARY KEY,
    holiday_name TEXT NOT NULL UNIQUE
);
CREATE TABLE weather_observations (
    weather_id INTEGER PRIMARY KEY,
    temp REAL,
    rain_1h REAL,
    snow_1h REAL,
    clouds_all INTEGER,
    weather_main TEXT,
    weather_description TEXT
);
CREATE TABLE traffic_observations (
    traffic_id INTEGER PRIMARY KEY,
    source_row INTEGER NOT NULL UNIQUE,
    date_time TEXT NOT NULL,
    traffic_volume INTEGER NOT NULL,
    holiday_id INTEGER REFERENCES holidays(holiday_id),
    weather_id INTEGER NOT NULL REFERENCES weather_observations(weather_id)
);
"""


def load_sqlite_fixture(connection: sqlite3.Connection, data: pd.DataFrame) -> None:
    connection.executescript(SQL_SETUP)
    holiday_ids: dict[str, int] = {}

    for source_row, row in enumerate(data.to_dict(orient="records"), start=1):
        holiday_name = row["holiday"]
        holiday_id = None
        if holiday_name != "None":
            if holiday_name not in holiday_ids:
                cursor = connection.execute(
                    "INSERT INTO holidays (holiday_name) VALUES (?)",
                    (holiday_name,),
                )
                holiday_ids[holiday_name] = int(cursor.lastrowid)
            holiday_id = holiday_ids[holiday_name]

        weather_cursor = connection.execute(
            """
            INSERT INTO weather_observations (
                temp, rain_1h, snow_1h, clouds_all,
                weather_main, weather_description
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                row["temp"],
                row["rain_1h"],
                row["snow_1h"],
                float(row["clouds_all"]),
                row["weather_main"],
                row["weather_description"],
            ),
        )
        connection.execute(
            """
            INSERT INTO traffic_observations (
                source_row, date_time, traffic_volume, holiday_id, weather_id
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                source_row,
                row["date_time"].strftime("%Y-%m-%d %H:%M:%S"),
                int(row["traffic_volume"]),
                holiday_id,
                int(weather_cursor.lastrowid),
            ),
        )
    connection.commit()


def format_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No matching rows._"

    def format_value(value: object) -> str:
        if pd.isna(value):
            return "NULL"
        if isinstance(value, float):
            return f"{value:.3f}"
        return str(value).replace("|", "\\|").replace("\n", " ")

    headers = [str(column) for column in frame.columns]
    rows = [
        [format_value(value) for value in row]
        for row in frame.itertuples(index=False, name=None)
    ]
    separator = ["---"] * len(headers)
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(separator) + " |",
            *["| " + " | ".join(row) + " |" for row in rows],
        ]
    )


def run_queries(csv_path: Path, output_path: Path) -> None:
    if not csv_path.is_file():
        raise FileNotFoundError(f"Prepared CSV not found: {csv_path}")
    data = pd.read_csv(
        csv_path,
        parse_dates=["date_time"],
        keep_default_na=False,
    )
    connection = sqlite3.connect(":memory:")
    try:
        load_sqlite_fixture(connection, data)

        latest_sql = pd.read_sql_query(
            """
            SELECT t.date_time, t.traffic_volume, h.holiday_name,
                   w.temp, w.rain_1h, w.snow_1h, w.clouds_all,
                   w.weather_main, w.weather_description
            FROM traffic_observations AS t
            JOIN weather_observations AS w ON w.weather_id = t.weather_id
            LEFT JOIN holidays AS h ON h.holiday_id = t.holiday_id
            ORDER BY t.date_time DESC, t.source_row DESC
            LIMIT 1
            """,
            connection,
        )
        date_range_sql = pd.read_sql_query(
            """
            SELECT t.date_time, t.traffic_volume, h.holiday_name,
                   w.weather_main, w.weather_description
            FROM traffic_observations AS t
            JOIN weather_observations AS w ON w.weather_id = t.weather_id
            LEFT JOIN holidays AS h ON h.holiday_id = t.holiday_id
            WHERE t.date_time >= '2016-01-01 00:00:00'
              AND t.date_time <  '2016-02-01 00:00:00'
            ORDER BY t.date_time, t.source_row
            """,
            connection,
        )
        date_range_count = len(date_range_sql)
        date_range_preview = date_range_sql.head(5)
        hourly_sql = pd.read_sql_query(
            """
            SELECT CAST(substr(date_time, 12, 2) AS INTEGER) AS hour_of_day,
                   AVG(traffic_volume) AS average_traffic_volume,
                   COUNT(*) AS observation_count
            FROM traffic_observations
            GROUP BY hour_of_day
            ORDER BY hour_of_day
            """,
            connection,
        )
        holiday_sql = pd.read_sql_query(
            """
            SELECT h.holiday_name,
                   AVG(t.traffic_volume) AS average_traffic_volume,
                   COUNT(*) AS observation_count
            FROM traffic_observations AS t
            JOIN holidays AS h ON h.holiday_id = t.holiday_id
            GROUP BY h.holiday_id, h.holiday_name
            ORDER BY average_traffic_volume DESC
            """,
            connection,
        )
    finally:
        connection.close()

    # These frames match the find and aggregation results from queries.js.
    mongo_latest = latest_sql.rename(columns={"holiday_name": "holiday"})
    mongo_date_range_preview = date_range_preview.rename(
        columns={"holiday_name": "holiday"}
    )
    mongo_hourly = hourly_sql.rename(columns={"hour_of_day": "_id"})
    mongo_holiday = holiday_sql.rename(columns={"holiday_name": "_id"})

    output = [
        "# Task 2 query results from the Part 1 cleaned dataset",
        "",
        f"- Input: `{csv_path}`",
        f"- Cleaned observations: **{len(data):,}**",
        "- The SQL results below were executed using SQLite against an in-memory relational "
        "copy of the actual cleaned CSV. The MongoDB aggregation equivalents are computed "
        "from the same CSV. Neither live MySQL nor MongoDB is installed in this environment; "
        "the repository's MySQL and MongoDB query files still need to be run against the "
        "respective servers for database-execution evidence.",
        "- Date range: 2016-01-01 inclusive to 2016-02-01 exclusive.",
        "",
        "## SQL query 1 — Latest observation",
        "",
        format_table(latest_sql),
        "",
        "## SQL query 2 — Date-range observations",
        "",
        f"Matching rows: **{date_range_count:,}**. First five rows:",
        "",
        format_table(date_range_preview),
        "",
        "## SQL query 3 — Average traffic by hour",
        "",
        format_table(hourly_sql),
        "",
        "## SQL query 4 — Average traffic on holidays",
        "",
        format_table(holiday_sql),
        "",
        "## MongoDB aggregation 1 — Average traffic by hour",
        "",
        format_table(mongo_hourly),
        "",
        "## MongoDB aggregation 2 — Average traffic on holidays",
        "",
        format_table(mongo_holiday),
        "",
        "## MongoDB query 1 — Latest observation",
        "",
        format_table(mongo_latest),
        "",
        "## MongoDB query 2 — Date-range observations",
        "",
        f"Matching documents: **{date_range_count:,}**. First five documents:",
        "",
        format_table(mongo_date_range_preview),
        "",
        "The MongoDB query script returns every document matching the date range; this report "
        "shows five rows to keep the output readable.",
        "",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(output), encoding="utf-8")
    print(f"Saved actual-data query results to {output_path}")
    print(f"Cleaned records loaded into SQLite: {len(data):,}")
    print(f"Records in the selected date range: {date_range_count:,}")
    print("Latest observation:")
    print(latest_sql.to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reproduce Task 2 query results against the prepared CSV."
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        default=Path("data/cleaned_traffic.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/task2_query_results.md"),
    )
    args = parser.parse_args()
    run_queries(args.csv_path, args.output)


if __name__ == "__main__":
    main()
