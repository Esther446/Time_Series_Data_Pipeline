"""Verify all Task 3 FastAPI CRUD and time-series endpoints for MySQL and MongoDB.

By default, this script loads the Part 1 cleaned dataset (40,575 observations) into
an in-memory relational SQLite adapter (mirroring the 3-table MySQL schema) and an
in-memory document collection adapter (mirroring the MongoDB collection), then
executes all CRUD (POST, GET, PUT, DELETE) and time-series (latest, date-range)
requests through FastAPI's TestClient and writes the evidence to
outputs/task3_api_results.md.

Pass --live to run the requests against live MySQL and MongoDB servers configured
via environment variables / .env.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.database import get_mongo_collection, get_sql_connection
from api.main import app
from scripts.prepare_data import prepare_data
from scripts.query_actual_data import load_sqlite_fixture


class MySQLCompatibleCursor:
    """Wrap a sqlite3.Cursor so %s placeholders and dictionary=True work identically to mysql.connector."""

    def __init__(self, conn: sqlite3.Connection, dictionary: bool = False) -> None:
        self._conn = conn
        self._cursor = conn.cursor()
        self._dictionary = dictionary
        self.lastrowid: int | None = None

    def execute(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> None:
        sqlite_query = query.replace("%s", "?")
        self._cursor.execute(sqlite_query, tuple(params))
        self.lastrowid = self._cursor.lastrowid

    def fetchone(self) -> Any:
        row = self._cursor.fetchone()
        if row is None:
            return None
        if self._dictionary:
            columns = [col[0] for col in self._cursor.description]
            return dict(zip(columns, row))
        return row

    def fetchall(self) -> list[Any]:
        rows = self._cursor.fetchall()
        if self._dictionary:
            columns = [col[0] for col in self._cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        return rows

    def close(self) -> None:
        self._cursor.close()


class MySQLCompatibleConnection:
    """Wrap a sqlite3.Connection to mimic mysql.connector connection methods."""

    def __init__(self, sqlite_conn: sqlite3.Connection) -> None:
        self._conn = sqlite_conn

    def cursor(self, dictionary: bool = False) -> MySQLCompatibleCursor:
        return MySQLCompatibleCursor(self._conn, dictionary=dictionary)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()


class InMemoryCursor:
    """Chainable cursor mimicking pymongo Cursor (.sort, .skip, .limit)."""

    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self._docs = docs

    def sort(self, key_or_list: list[tuple[str, int]]) -> InMemoryCursor:
        for field, direction in reversed(key_or_list):
            reverse = direction < 0
            self._docs.sort(key=lambda d: d.get(field), reverse=reverse)
        return self

    def skip(self, count: int) -> InMemoryCursor:
        self._docs = self._docs[count:]
        return self

    def limit(self, count: int) -> InMemoryCursor:
        self._docs = self._docs[:count]
        return self

    def __iter__(self):
        return iter(self._docs)


class DeleteResultStub:
    def __init__(self, deleted_count: int) -> None:
        self.deleted_count = deleted_count


class InMemoryMongoCollection:
    """In-memory MongoDB Collection adapter for reproducible verification of mongodb_crud."""

    def __init__(self, initial_docs: list[dict[str, Any]]) -> None:
        self._store: dict[Any, dict[str, Any]] = {
            doc["_id"]: doc for doc in initial_docs
        }

    def _matches(self, doc: dict[str, Any], filter_spec: dict[str, Any]) -> bool:
        if not filter_spec:
            return True
        for key, cond in filter_spec.items():
            if key == "$or":
                if not any(self._matches(doc, sub) for sub in cond):
                    return False
            elif isinstance(cond, dict):
                val = doc.get(key)
                for op, target in cond.items():
                    if op == "$gte" and not (val is not None and val >= target):
                        return False
                    if op == "$lt" and not (val is not None and val < target):
                        return False
            else:
                if doc.get(key) != cond:
                    return False
        return True

    def find_one(
        self,
        filter_spec: dict[str, Any] | None = None,
        projection: dict[str, int] | None = None,
        sort: list[tuple[str, int]] | None = None,
    ) -> dict[str, Any] | None:
        cursor = self.find(filter_spec or {})
        if sort:
            cursor = cursor.sort(sort)
        results = list(cursor.limit(1))
        return dict(results[0]) if results else None

    def find(self, filter_spec: dict[str, Any] | None = None) -> InMemoryCursor:
        spec = filter_spec or {}
        matched = [
            dict(doc) for doc in self._store.values() if self._matches(doc, spec)
        ]
        return InMemoryCursor(matched)

    def insert_one(self, document: dict[str, Any]) -> None:
        doc_id = document["_id"]
        if doc_id in self._store:
            raise DuplicateKeyError(f"Duplicate _id: {doc_id}")
        self._store[doc_id] = dict(document)

    def update_one(self, filter_spec: dict[str, Any], update_spec: dict[str, Any]) -> None:
        for doc_id, doc in self._store.items():
            if self._matches(doc, filter_spec):
                if "$set" in update_spec:
                    doc.update(update_spec["$set"])
                self._store[doc_id] = doc
                return

    def delete_one(self, filter_spec: dict[str, Any]) -> DeleteResultStub:
        for doc_id, doc in list(self._store.items()):
            if self._matches(doc, filter_spec):
                del self._store[doc_id]
                return DeleteResultStub(deleted_count=1)
        return DeleteResultStub(deleted_count=0)


def build_mongo_docs_from_dataframe(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Build MongoDB documents matching load_mongodb.py from the cleaned DataFrame."""
    docs: list[dict[str, Any]] = []
    for source_row, row in enumerate(df.to_dict(orient="records"), start=1):
        holiday_val = None if row["holiday"] == "None" else str(row["holiday"])
        clouds = float(row["clouds_all"])
        clouds_clean: int | float = int(clouds) if clouds.is_integer() else clouds
        docs.append(
            {
                "_id": source_row,
                "source_row": source_row,
                "date_time": row["date_time"].to_pydatetime(),
                "traffic_volume": int(row["traffic_volume"]),
                "holiday": holiday_val,
                "weather": {
                    "temp": float(row["temp"]),
                    "rain_1h": float(row["rain_1h"]),
                    "snow_1h": float(row["snow_1h"]),
                    "clouds_all": clouds_clean,
                    "weather_main": str(row["weather_main"]),
                    "weather_description": str(row["weather_description"]),
                },
            }
        )
    return docs


def run_verification(
    csv_path: Path,
    output_path: Path,
    use_live_dbs: bool = False,
) -> None:
    if not csv_path.is_file():
        raw_candidates = [
            PROJECT_ROOT / "data" / "Metro_Interstate_Traffic_Volume.csv",
            PROJECT_ROOT / "Data" / "Metro_Interstate_Traffic_Volume.csv",
        ]
        source_csv = next((p for p in raw_candidates if p.is_file()), None)
        if source_csv is None:
            raise FileNotFoundError(
                f"Neither {csv_path} nor Metro_Interstate_Traffic_Volume.csv was found."
            )
        prepare_data(source_csv, csv_path)

    sqlite_conn: sqlite3.Connection | None = None
    if not use_live_dbs:
        data = pd.read_csv(
            csv_path,
            parse_dates=["date_time"],
            keep_default_na=False,
        )
        sqlite_conn = sqlite3.connect(":memory:", check_same_thread=False)
        load_sqlite_fixture(sqlite_conn, data)
        sql_wrapper = MySQLCompatibleConnection(sqlite_conn)
        mongo_collection = InMemoryMongoCollection(
            build_mongo_docs_from_dataframe(data)
        )

        app.dependency_overrides[get_sql_connection] = lambda: sql_wrapper
        app.dependency_overrides[get_mongo_collection] = lambda: mongo_collection

    client = TestClient(app)
    report_lines = [
        "# Task 3 API CRUD & Time-Series Endpoint Verification Results",
        "",
        f"- **Dataset input:** `{csv_path}` (40,575 cleaned observations)",
        f"- **Execution mode:** {'Live MySQL & MongoDB servers' if use_live_dbs else 'FastAPI TestClient against full 40,575-row MySQL & MongoDB fixtures'}",
        "",
    ]

    try:
        for db_label, prefix in [("MySQL", "/api/sql/records"), ("MongoDB", "/api/mongodb/records")]:
            report_lines.append(f"## {db_label} Endpoints (`{prefix}`)")
            report_lines.append("")

            # 1. GET Latest Record
            res_latest = client.get(f"{prefix}/latest")
            assert res_latest.status_code == 200, res_latest.text
            latest_body = res_latest.json()
            report_lines.extend(
                [
                    f"### 1. Latest Record — `GET {prefix}/latest`",
                    f"- **Status:** `{res_latest.status_code} OK`",
                    "```json",
                    json.dumps(latest_body, indent=2),
                    "```",
                    "",
                ]
            )

            # 2. GET Records by Date Range
            start_q = "2016-01-01T00:00:00"
            end_q = "2016-02-01T00:00:00"
            res_range = client.get(
                f"{prefix}/date-range",
                params={"start": start_q, "end": end_q, "limit": 1000},
            )
            assert res_range.status_code == 200, res_range.text
            range_list = res_range.json()
            report_lines.extend(
                [
                    f"### 2. Records by Date Range — `GET {prefix}/date-range?start={start_q}&end={end_q}`",
                    f"- **Status:** `{res_range.status_code} OK`",
                    f"- **Matching records returned:** **{len(range_list)}**",
                    "- **First 2 records in range:**",
                    "```json",
                    json.dumps(range_list[:2], indent=2),
                    "```",
                    "",
                ]
            )

            # 3. POST (Create) Record
            create_payload = {
                "date_time": "2018-10-01T00:00:00",
                "traffic_volume": 1240,
                "holiday": None,
                "weather": {
                    "temp": 282.45,
                    "rain_1h": 0.0,
                    "snow_1h": 0.0,
                    "clouds_all": 75.0,
                    "weather_main": "Clouds",
                    "weather_description": "broken clouds",
                },
            }
            res_post = client.post(prefix, json=create_payload)
            assert res_post.status_code == 201, res_post.text
            created_body = res_post.json()
            created_id = created_body["source_row"]
            report_lines.extend(
                [
                    f"### 3. Create Record (POST) — `POST {prefix}`",
                    f"- **Status:** `{res_post.status_code} Created`",
                    "```json",
                    json.dumps(created_body, indent=2),
                    "```",
                    "",
                ]
            )

            # 4. GET Single Record by source_row
            res_get = client.get(f"{prefix}/{created_id}")
            assert res_get.status_code == 200, res_get.text
            get_body = res_get.json()
            report_lines.extend(
                [
                    f"### 4. Read Record by ID (GET) — `GET {prefix}/{created_id}`",
                    f"- **Status:** `{res_get.status_code} OK`",
                    "```json",
                    json.dumps(get_body, indent=2),
                    "```",
                    "",
                ]
            )

            # 5. PUT (Update) Record
            update_payload = {
                "traffic_volume": 1580,
                "holiday": "Test Regional Holiday",
                "weather": {
                    "temp": 284.0,
                    "clouds_all": 20.0,
                    "weather_main": "Clear",
                    "weather_description": "sky is clear",
                },
            }
            res_put = client.put(f"{prefix}/{created_id}", json=update_payload)
            assert res_put.status_code == 200, res_put.text
            updated_body = res_put.json()
            assert updated_body["traffic_volume"] == 1580
            assert updated_body["holiday"] == "Test Regional Holiday"
            report_lines.extend(
                [
                    f"### 5. Update Record (PUT) — `PUT {prefix}/{created_id}`",
                    f"- **Status:** `{res_put.status_code} OK`",
                    "```json",
                    json.dumps(updated_body, indent=2),
                    "```",
                    "",
                ]
            )

            # 6. DELETE Record
            res_delete = client.delete(f"{prefix}/{created_id}")
            assert res_delete.status_code == 200, res_delete.text
            delete_body = res_delete.json()
            res_after_delete = client.get(f"{prefix}/{created_id}")
            assert res_after_delete.status_code == 404
            report_lines.extend(
                [
                    f"### 6. Delete Record (DELETE) — `DELETE {prefix}/{created_id}`",
                    f"- **Status:** `{res_delete.status_code} OK` (subsequent GET verified `404 Not Found`)",
                    "```json",
                    json.dumps(delete_body, indent=2),
                    "```",
                    "",
                ]
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(report_lines), encoding="utf-8")
        print(f"All MySQL and MongoDB CRUD + Time-Series endpoints verified! Saved report to {output_path}")
    finally:
        app.dependency_overrides.clear()
        if sqlite_conn is not None:
            sqlite_conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify Task 3 CRUD and time-series endpoints for MySQL and MongoDB."
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
        default=Path("outputs/task3_api_results.md"),
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run verification against live MySQL and MongoDB servers instead of in-memory fixtures.",
    )
    args = parser.parse_args()
    run_verification(args.csv_path, args.output, use_live_dbs=args.live)


if __name__ == "__main__":
    main()

