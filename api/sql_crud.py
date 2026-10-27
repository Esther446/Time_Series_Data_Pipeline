"""Relational (MySQL) CRUD and time-series query operations for Task 3."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException, status

from api.schemas import (
    DeleteRecordResponse,
    TrafficRecordCreate,
    TrafficRecordResponse,
    TrafficRecordUpdate,
    WeatherObservation,
)

SELECT_JOINED_BASE = """
SELECT
    t.source_row,
    t.date_time,
    t.traffic_volume,
    h.holiday_name AS holiday,
    w.temp,
    w.rain_1h,
    w.snow_1h,
    w.clouds_all,
    w.weather_main,
    w.weather_description
FROM traffic_observations AS t
JOIN weather_observations AS w ON w.weather_id = t.weather_id
LEFT JOIN holidays AS h ON h.holiday_id = t.holiday_id
"""


def _row_to_response(row: dict[str, Any]) -> TrafficRecordResponse:
    """Convert a joined SQL dictionary row into a TrafficRecordResponse."""
    raw_dt = row["date_time"]
    if isinstance(raw_dt, str):
        dt = datetime.fromisoformat(raw_dt)
    else:
        dt = raw_dt

    return TrafficRecordResponse(
        source_row=int(row["source_row"]),
        date_time=dt,
        traffic_volume=int(row["traffic_volume"]),
        holiday=row.get("holiday"),
        weather=WeatherObservation(
            temp=float(row["temp"]) if row.get("temp") is not None else None,
            rain_1h=float(row["rain_1h"]) if row.get("rain_1h") is not None else None,
            snow_1h=float(row["snow_1h"]) if row.get("snow_1h") is not None else None,
            clouds_all=(
                float(row["clouds_all"]) if row.get("clouds_all") is not None else None
            ),
            weather_main=row.get("weather_main"),
            weather_description=row.get("weather_description"),
        ),
    )


def _resolve_or_create_holiday_id(cursor: Any, holiday_name: str | None) -> int | None:
    """Return the holiday_id for holiday_name, inserting a new row if needed."""
    if holiday_name is None:
        return None

    cursor.execute(
        "SELECT holiday_id FROM holidays WHERE holiday_name = %s",
        (holiday_name,),
    )
    existing = cursor.fetchone()
    if existing is not None:
        return int(existing["holiday_id"] if isinstance(existing, dict) else existing[0])

    cursor.execute(
        "INSERT INTO holidays (holiday_name) VALUES (%s)",
        (holiday_name,),
    )
    return int(cursor.lastrowid)


def create_sql_record(
    connection: Any,
    payload: TrafficRecordCreate,
) -> TrafficRecordResponse:
    """Insert a new traffic observation across holidays, weather_observations, and traffic_observations."""
    cursor = connection.cursor(dictionary=True)
    try:
        if payload.source_row is not None:
            cursor.execute(
                "SELECT 1 FROM traffic_observations WHERE source_row = %s",
                (payload.source_row,),
            )
            if cursor.fetchone() is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Record with source_row={payload.source_row} already exists in MySQL.",
                )
            source_row = payload.source_row
        else:
            cursor.execute(
                "SELECT COALESCE(MAX(source_row), 0) + 1 AS next_row FROM traffic_observations"
            )
            next_row = cursor.fetchone()
            source_row = int(next_row["next_row"]) if next_row else 1

        holiday_id = _resolve_or_create_holiday_id(cursor, payload.holiday)

        weather = payload.weather
        cursor.execute(
            """
            INSERT INTO weather_observations (
                temp, rain_1h, snow_1h, clouds_all,
                weather_main, weather_description
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                weather.temp,
                weather.rain_1h,
                weather.snow_1h,
                weather.clouds_all,
                weather.weather_main,
                weather.weather_description,
            ),
        )
        weather_id = int(cursor.lastrowid)

        cursor.execute(
            """
            INSERT INTO traffic_observations (
                source_row, date_time, traffic_volume, holiday_id, weather_id
            ) VALUES (%s, %s, %s, %s, %s)
            """,
            (
                source_row,
                payload.date_time.strftime("%Y-%m-%d %H:%M:%S"),
                payload.traffic_volume,
                holiday_id,
                weather_id,
            ),
        )
        connection.commit()
    except HTTPException:
        connection.rollback()
        raise
    except Exception as error:
        connection.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create MySQL traffic record: {error}",
        ) from error
    finally:
        cursor.close()

    return get_sql_record_by_source_row(connection, source_row)


def get_sql_latest_record(connection: Any) -> TrafficRecordResponse:
    """Return the most recent observation ordered by date_time DESC, source_row DESC."""
    records = get_sql_latest_records(connection, limit=1)
    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No traffic observations found in MySQL.",
        )
    return records[0]


def get_sql_latest_records(
    connection: Any,
    limit: int = 1,
) -> list[TrafficRecordResponse]:
    """Return the latest N observations ordered by date_time DESC, source_row DESC."""
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            SELECT_JOINED_BASE
            + " ORDER BY t.date_time DESC, t.source_row DESC LIMIT %s",
            (limit,),
        )
        rows = cursor.fetchall()
        return [_row_to_response(row) for row in rows]
    finally:
        cursor.close()


def get_sql_records_by_date_range(
    connection: Any,
    start: datetime,
    end: datetime,
    limit: int = 500,
    offset: int = 0,
) -> list[TrafficRecordResponse]:
    """Return observations in the half-open interval [start, end) ordered chronologically."""
    if end <= start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'end' timestamp must be strictly greater than 'start' timestamp.",
        )

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            SELECT_JOINED_BASE
            + """
            WHERE t.date_time >= %s
              AND t.date_time <  %s
            ORDER BY t.date_time ASC, t.source_row ASC
            LIMIT %s OFFSET %s
            """,
            (
                start.strftime("%Y-%m-%d %H:%M:%S"),
                end.strftime("%Y-%m-%d %H:%M:%S"),
                limit,
                offset,
            ),
        )
        rows = cursor.fetchall()
        return [_row_to_response(row) for row in rows]
    finally:
        cursor.close()


def get_sql_record_by_source_row(
    connection: Any,
    source_row: int,
) -> TrafficRecordResponse:
    """Fetch a single traffic observation by its unique source_row."""
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            SELECT_JOINED_BASE + " WHERE t.source_row = %s",
            (source_row,),
        )
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Traffic record with source_row={source_row} not found in MySQL.",
            )
        return _row_to_response(row)
    finally:
        cursor.close()


def list_sql_records(
    connection: Any,
    limit: int = 100,
    offset: int = 0,
) -> list[TrafficRecordResponse]:
    """Return a paginated list of traffic observations ordered chronologically."""
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            SELECT_JOINED_BASE
            + " ORDER BY t.date_time ASC, t.source_row ASC LIMIT %s OFFSET %s",
            (limit, offset),
        )
        rows = cursor.fetchall()
        return [_row_to_response(row) for row in rows]
    finally:
        cursor.close()


def update_sql_record(
    connection: Any,
    source_row: int,
    payload: TrafficRecordUpdate,
) -> TrafficRecordResponse:
    """Update an existing traffic observation and its joined weather/holiday records."""
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT t.traffic_id, t.date_time, t.traffic_volume, t.holiday_id, t.weather_id,
                   h.holiday_name AS holiday,
                   w.temp, w.rain_1h, w.snow_1h, w.clouds_all,
                   w.weather_main, w.weather_description
            FROM traffic_observations AS t
            JOIN weather_observations AS w ON w.weather_id = t.weather_id
            LEFT JOIN holidays AS h ON h.holiday_id = t.holiday_id
            WHERE t.source_row = %s
            """,
            (source_row,),
        )
        existing = cursor.fetchone()
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Traffic record with source_row={source_row} not found in MySQL.",
            )

        fields_set = payload.model_fields_set

        new_dt = (
            payload.date_time.strftime("%Y-%m-%d %H:%M:%S")
            if "date_time" in fields_set and payload.date_time is not None
            else (
                existing["date_time"].strftime("%Y-%m-%d %H:%M:%S")
                if isinstance(existing["date_time"], datetime)
                else str(existing["date_time"])
            )
        )
        new_volume = (
            payload.traffic_volume
            if "traffic_volume" in fields_set and payload.traffic_volume is not None
            else int(existing["traffic_volume"])
        )

        if "holiday" in fields_set:
            holiday_id = _resolve_or_create_holiday_id(cursor, payload.holiday)
        else:
            holiday_id = existing["holiday_id"]

        if "weather" in fields_set and payload.weather is not None:
            w_set = payload.weather.model_fields_set
            w = payload.weather
            cursor.execute(
                """
                UPDATE weather_observations
                SET temp = %s,
                    rain_1h = %s,
                    snow_1h = %s,
                    clouds_all = %s,
                    weather_main = %s,
                    weather_description = %s
                WHERE weather_id = %s
                """,
                (
                    w.temp if "temp" in w_set else existing["temp"],
                    w.rain_1h if "rain_1h" in w_set else existing["rain_1h"],
                    w.snow_1h if "snow_1h" in w_set else existing["snow_1h"],
                    w.clouds_all if "clouds_all" in w_set else existing["clouds_all"],
                    w.weather_main if "weather_main" in w_set else existing["weather_main"],
                    (
                        w.weather_description
                        if "weather_description" in w_set
                        else existing["weather_description"]
                    ),
                    existing["weather_id"],
                ),
            )

        cursor.execute(
            """
            UPDATE traffic_observations
            SET date_time = %s,
                traffic_volume = %s,
                holiday_id = %s
            WHERE source_row = %s
            """,
            (new_dt, new_volume, holiday_id, source_row),
        )
        connection.commit()
    except HTTPException:
        connection.rollback()
        raise
    except Exception as error:
        connection.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update MySQL traffic record: {error}",
        ) from error
    finally:
        cursor.close()

    return get_sql_record_by_source_row(connection, source_row)


def delete_sql_record(
    connection: Any,
    source_row: int,
) -> DeleteRecordResponse:
    """Delete a traffic observation and its associated weather_observations row."""
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT traffic_id, weather_id FROM traffic_observations WHERE source_row = %s",
            (source_row,),
        )
        existing = cursor.fetchone()
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Traffic record with source_row={source_row} not found in MySQL.",
            )

        weather_id = existing["weather_id"]
        cursor.execute(
            "DELETE FROM traffic_observations WHERE source_row = %s",
            (source_row,),
        )
        cursor.execute(
            "DELETE FROM weather_observations WHERE weather_id = %s",
            (weather_id,),
        )
        connection.commit()
    except HTTPException:
        connection.rollback()
        raise
    except Exception as error:
        connection.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete MySQL traffic record: {error}",
        ) from error
    finally:
        cursor.close()

    return DeleteRecordResponse(
        database="mysql",
        source_row=source_row,
        deleted=True,
        message=f"Deleted traffic observation source_row={source_row} from MySQL.",
    )
