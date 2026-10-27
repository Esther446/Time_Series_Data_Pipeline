"""Non-relational (MongoDB) CRUD and time-series query operations for Task 3."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from pymongo import ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError, PyMongoError

from api.schemas import (
    DeleteRecordResponse,
    TrafficRecordCreate,
    TrafficRecordResponse,
    TrafficRecordUpdate,
    WeatherObservation,
)


def _doc_to_response(doc: dict[str, Any]) -> TrafficRecordResponse:
    """Convert a MongoDB traffic_observations document into a TrafficRecordResponse."""
    raw_dt = doc["date_time"]
    if isinstance(raw_dt, str):
        dt = datetime.fromisoformat(raw_dt.replace("Z", "+00:00")).replace(tzinfo=None)
    elif isinstance(raw_dt, datetime) and raw_dt.tzinfo is not None:
        dt = raw_dt.replace(tzinfo=None)
    else:
        dt = raw_dt

    weather_raw = doc.get("weather") or {}
    source_row = int(doc.get("source_row", doc.get("_id")))

    return TrafficRecordResponse(
        source_row=source_row,
        date_time=dt,
        traffic_volume=int(doc["traffic_volume"]),
        holiday=doc.get("holiday"),
        weather=WeatherObservation(
            temp=weather_raw.get("temp"),
            rain_1h=weather_raw.get("rain_1h"),
            snow_1h=weather_raw.get("snow_1h"),
            clouds_all=weather_raw.get("clouds_all"),
            weather_main=weather_raw.get("weather_main"),
            weather_description=weather_raw.get("weather_description"),
        ),
    )


def _next_mongo_source_row(collection: Collection[dict[str, Any]]) -> int:
    """Determine the next sequential source_row in the MongoDB collection."""
    top_doc = collection.find_one(
        {},
        projection={"source_row": 1, "_id": 1},
        sort=[("source_row", DESCENDING)],
    )
    if top_doc is None:
        return 1
    current_max = top_doc.get("source_row") or top_doc.get("_id") or 0
    return int(current_max) + 1


def create_mongo_record(
    collection: Collection[dict[str, Any]],
    payload: TrafficRecordCreate,
) -> TrafficRecordResponse:
    """Insert a new traffic observation document into MongoDB."""
    try:
        if payload.source_row is not None:
            existing = collection.find_one(
                {"$or": [{"_id": payload.source_row}, {"source_row": payload.source_row}]}
            )
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Record with source_row={payload.source_row} "
                        "already exists in MongoDB."
                    ),
                )
            source_row = payload.source_row
        else:
            source_row = _next_mongo_source_row(collection)

        clouds_val: int | float | None = payload.weather.clouds_all
        if clouds_val is not None and float(clouds_val).is_integer():
            clouds_val = int(clouds_val)

        document: dict[str, Any] = {
            "_id": source_row,
            "source_row": source_row,
            "date_time": payload.date_time,
            "traffic_volume": payload.traffic_volume,
            "holiday": payload.holiday,
            "weather": {
                "temp": payload.weather.temp,
                "rain_1h": payload.weather.rain_1h,
                "snow_1h": payload.weather.snow_1h,
                "clouds_all": clouds_val,
                "weather_main": payload.weather.weather_main,
                "weather_description": payload.weather.weather_description,
            },
        }
        collection.insert_one(document)
        return _doc_to_response(document)
    except HTTPException:
        raise
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Record with source_row={payload.source_row} already exists in MongoDB.",
        ) from error
    except PyMongoError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MongoDB operation failed: {error}",
        ) from error


def get_mongo_latest_record(
    collection: Collection[dict[str, Any]],
) -> TrafficRecordResponse:
    """Return the latest observation ordered by date_time DESC, source_row DESC."""
    records = get_mongo_latest_records(collection, limit=1)
    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No traffic observations found in MongoDB.",
        )
    return records[0]


def get_mongo_latest_records(
    collection: Collection[dict[str, Any]],
    limit: int = 1,
) -> list[TrafficRecordResponse]:
    """Return the latest N observations ordered by date_time DESC, source_row DESC."""
    try:
        cursor = (
            collection.find({})
            .sort([("date_time", DESCENDING), ("source_row", DESCENDING)])
            .limit(limit)
        )
        return [_doc_to_response(doc) for doc in cursor]
    except PyMongoError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MongoDB query failed: {error}",
        ) from error


def get_mongo_records_by_date_range(
    collection: Collection[dict[str, Any]],
    start: datetime,
    end: datetime,
    limit: int = 500,
    offset: int = 0,
) -> list[TrafficRecordResponse]:
    """Return observations in the half-open date range [start, end) ordered chronologically."""
    if end <= start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'end' timestamp must be strictly greater than 'start' timestamp.",
        )
    try:
        cursor = (
            collection.find(
                {
                    "date_time": {
                        "$gte": start,
                        "$lt": end,
                    }
                }
            )
            .sort([("date_time", ASCENDING), ("source_row", ASCENDING)])
            .skip(offset)
            .limit(limit)
        )
        return [_doc_to_response(doc) for doc in cursor]
    except PyMongoError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MongoDB date-range query failed: {error}",
        ) from error


def get_mongo_record_by_source_row(
    collection: Collection[dict[str, Any]],
    source_row: int,
) -> TrafficRecordResponse:
    """Fetch a single MongoDB traffic observation document by source_row."""
    try:
        doc = collection.find_one(
            {"$or": [{"source_row": source_row}, {"_id": source_row}]}
        )
    except PyMongoError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MongoDB lookup failed: {error}",
        ) from error

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Traffic record with source_row={source_row} not found in MongoDB.",
        )
    return _doc_to_response(doc)


def list_mongo_records(
    collection: Collection[dict[str, Any]],
    limit: int = 100,
    offset: int = 0,
) -> list[TrafficRecordResponse]:
    """Return a paginated list of MongoDB traffic observations ordered chronologically."""
    try:
        cursor = (
            collection.find({})
            .sort([("date_time", ASCENDING), ("source_row", ASCENDING)])
            .skip(offset)
            .limit(limit)
        )
        return [_doc_to_response(doc) for doc in cursor]
    except PyMongoError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MongoDB list query failed: {error}",
        ) from error


def update_mongo_record(
    collection: Collection[dict[str, Any]],
    source_row: int,
    payload: TrafficRecordUpdate,
) -> TrafficRecordResponse:
    """Update an existing MongoDB traffic observation document by source_row."""
    try:
        existing = collection.find_one(
            {"$or": [{"source_row": source_row}, {"_id": source_row}]}
        )
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Traffic record with source_row={source_row} not found in MongoDB.",
            )

        fields_set = payload.model_fields_set
        updates: dict[str, Any] = {}

        if "date_time" in fields_set and payload.date_time is not None:
            updates["date_time"] = payload.date_time
        if "traffic_volume" in fields_set and payload.traffic_volume is not None:
            updates["traffic_volume"] = payload.traffic_volume
        if "holiday" in fields_set:
            updates["holiday"] = payload.holiday

        if "weather" in fields_set and payload.weather is not None:
            existing_weather = dict(existing.get("weather") or {})
            w_set = payload.weather.model_fields_set
            w = payload.weather
            for key in (
                "temp",
                "rain_1h",
                "snow_1h",
                "clouds_all",
                "weather_main",
                "weather_description",
            ):
                if key in w_set:
                    val = getattr(w, key)
                    if (
                        key == "clouds_all"
                        and val is not None
                        and float(val).is_integer()
                    ):
                        val = int(val)
                    existing_weather[key] = val
            updates["weather"] = existing_weather

        if updates:
            collection.update_one(
                {"_id": existing["_id"]},
                {"$set": updates},
            )

        updated_doc = collection.find_one({"_id": existing["_id"]})
        assert updated_doc is not None
        return _doc_to_response(updated_doc)
    except HTTPException:
        raise
    except PyMongoError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to update MongoDB traffic record: {error}",
        ) from error


def delete_mongo_record(
    collection: Collection[dict[str, Any]],
    source_row: int,
) -> DeleteRecordResponse:
    """Delete a MongoDB traffic observation document by source_row."""
    try:
        result = collection.delete_one(
            {"$or": [{"source_row": source_row}, {"_id": source_row}]}
        )
    except PyMongoError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to delete MongoDB traffic record: {error}",
        ) from error

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Traffic record with source_row={source_row} not found in MongoDB.",
        )

    return DeleteRecordResponse(
        database="mongodb",
        source_row=source_row,
        deleted=True,
        message=f"Deleted traffic observation source_row={source_row} from MongoDB.",
    )
