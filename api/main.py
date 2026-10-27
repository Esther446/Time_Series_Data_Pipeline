"""FastAPI application exposing CRUD and time-series endpoints for MySQL and MongoDB."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from pymongo.collection import Collection

from api.database import get_mongo_collection, get_sql_connection
from api.mongodb_crud import (
    create_mongo_record,
    delete_mongo_record,
    get_mongo_latest_record,
    get_mongo_latest_records,
    get_mongo_record_by_source_row,
    get_mongo_records_by_date_range,
    list_mongo_records,
    update_mongo_record,
)
from api.schemas import (
    DeleteRecordResponse,
    TrafficRecordCreate,
    TrafficRecordResponse,
    TrafficRecordUpdate,
    parse_naive_datetime,
)
from api.sql_crud import (
    create_sql_record,
    delete_sql_record,
    get_sql_latest_record,
    get_sql_latest_records,
    get_sql_record_by_source_row,
    get_sql_records_by_date_range,
    list_sql_records,
    update_sql_record,
)

app = FastAPI(
    title="Metro Interstate Traffic Time-Series API",
    description=(
        "Task 3 REST API providing full CRUD (POST, GET, PUT, DELETE) and "
        "time-series queries (latest record, records by date range) for both "
        "MySQL (relational) and MongoDB (document) databases."
    ),
    version="1.0.0",
)

sql_router = APIRouter(prefix="/api/sql/records", tags=["MySQL CRUD & Time-Series"])
mongo_router = APIRouter(
    prefix="/api/mongodb/records", tags=["MongoDB CRUD & Time-Series"]
)


def _parse_query_timestamp(value: str, param_name: str):
    """Parse a query-parameter timestamp string into a timezone-naive datetime."""
    try:
        return parse_naive_datetime(value)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid '{param_name}' timestamp: {error}",
        ) from error


# ---------------------------------------------------------------------------
# MySQL Endpoints
# ---------------------------------------------------------------------------


@sql_router.post(
    "",
    response_model=TrafficRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new traffic record in MySQL",
)
def sql_create_record(
    payload: TrafficRecordCreate,
    connection: Any = Depends(get_sql_connection),
) -> TrafficRecordResponse:
    return create_sql_record(connection, payload)


@sql_router.get(
    "/latest",
    response_model=TrafficRecordResponse,
    summary="Get the latest traffic record from MySQL",
)
def sql_get_latest_record(
    connection: Any = Depends(get_sql_connection),
) -> TrafficRecordResponse:
    return get_sql_latest_record(connection)


@sql_router.get(
    "/recent",
    response_model=list[TrafficRecordResponse],
    summary="Get the N most recent traffic records from MySQL (useful for lag features)",
)
def sql_get_recent_records(
    limit: int = Query(
        default=25,
        ge=1,
        le=1000,
        description="Number of recent observations to return (ordered newest first)",
    ),
    connection: Any = Depends(get_sql_connection),
) -> list[TrafficRecordResponse]:
    return get_sql_latest_records(connection, limit=limit)


@sql_router.get(
    "/date-range",
    response_model=list[TrafficRecordResponse],
    summary="Get traffic records within a [start, end) date range from MySQL",
)
def sql_get_records_by_date_range(
    start: str = Query(
        ...,
        description="Inclusive start timestamp (e.g., '2016-01-01T00:00:00' or '2016-01-01 00:00:00')",
    ),
    end: str = Query(
        ...,
        description="Exclusive end timestamp (e.g., '2016-02-01T00:00:00' or '2016-02-01 00:00:00')",
    ),
    limit: int = Query(
        default=500,
        ge=1,
        le=5000,
        description="Maximum number of records to return",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of matching records to skip",
    ),
    connection: Any = Depends(get_sql_connection),
) -> list[TrafficRecordResponse]:
    start_dt = _parse_query_timestamp(start, "start")
    end_dt = _parse_query_timestamp(end, "end")
    return get_sql_records_by_date_range(
        connection, start=start_dt, end=end_dt, limit=limit, offset=offset
    )


@sql_router.get(
    "",
    response_model=list[TrafficRecordResponse],
    summary="List traffic records from MySQL with pagination",
)
def sql_list_records(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    connection: Any = Depends(get_sql_connection),
) -> list[TrafficRecordResponse]:
    return list_sql_records(connection, limit=limit, offset=offset)


@sql_router.get(
    "/{source_row}",
    response_model=TrafficRecordResponse,
    summary="Get a single traffic record by source_row from MySQL",
)
def sql_get_record(
    source_row: int,
    connection: Any = Depends(get_sql_connection),
) -> TrafficRecordResponse:
    return get_sql_record_by_source_row(connection, source_row)


@sql_router.put(
    "/{source_row}",
    response_model=TrafficRecordResponse,
    summary="Update a traffic record by source_row in MySQL",
)
def sql_update_record(
    source_row: int,
    payload: TrafficRecordUpdate,
    connection: Any = Depends(get_sql_connection),
) -> TrafficRecordResponse:
    return update_sql_record(connection, source_row, payload)


@sql_router.delete(
    "/{source_row}",
    response_model=DeleteRecordResponse,
    summary="Delete a traffic record by source_row from MySQL",
)
def sql_delete_record(
    source_row: int,
    connection: Any = Depends(get_sql_connection),
) -> DeleteRecordResponse:
    return delete_sql_record(connection, source_row)


# ---------------------------------------------------------------------------
# MongoDB Endpoints
# ---------------------------------------------------------------------------


@mongo_router.post(
    "",
    response_model=TrafficRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new traffic record in MongoDB",
)
def mongo_create_record(
    payload: TrafficRecordCreate,
    collection: Collection[dict[str, Any]] = Depends(get_mongo_collection),
) -> TrafficRecordResponse:
    return create_mongo_record(collection, payload)


@mongo_router.get(
    "/latest",
    response_model=TrafficRecordResponse,
    summary="Get the latest traffic record from MongoDB",
)
def mongo_get_latest_record(
    collection: Collection[dict[str, Any]] = Depends(get_mongo_collection),
) -> TrafficRecordResponse:
    return get_mongo_latest_record(collection)


@mongo_router.get(
    "/recent",
    response_model=list[TrafficRecordResponse],
    summary="Get the N most recent traffic records from MongoDB (useful for lag features)",
)
def mongo_get_recent_records(
    limit: int = Query(
        default=25,
        ge=1,
        le=1000,
        description="Number of recent observations to return (ordered newest first)",
    ),
    collection: Collection[dict[str, Any]] = Depends(get_mongo_collection),
) -> list[TrafficRecordResponse]:
    return get_mongo_latest_records(collection, limit=limit)


@mongo_router.get(
    "/date-range",
    response_model=list[TrafficRecordResponse],
    summary="Get traffic records within a [start, end) date range from MongoDB",
)
def mongo_get_records_by_date_range(
    start: str = Query(
        ...,
        description="Inclusive start timestamp (e.g., '2016-01-01T00:00:00' or '2016-01-01 00:00:00')",
    ),
    end: str = Query(
        ...,
        description="Exclusive end timestamp (e.g., '2016-02-01T00:00:00' or '2016-02-01 00:00:00')",
    ),
    limit: int = Query(
        default=500,
        ge=1,
        le=5000,
        description="Maximum number of records to return",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of matching records to skip",
    ),
    collection: Collection[dict[str, Any]] = Depends(get_mongo_collection),
) -> list[TrafficRecordResponse]:
    start_dt = _parse_query_timestamp(start, "start")
    end_dt = _parse_query_timestamp(end, "end")
    return get_mongo_records_by_date_range(
        collection, start=start_dt, end=end_dt, limit=limit, offset=offset
    )


@mongo_router.get(
    "",
    response_model=list[TrafficRecordResponse],
    summary="List traffic records from MongoDB with pagination",
)
def mongo_list_records(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    collection: Collection[dict[str, Any]] = Depends(get_mongo_collection),
) -> list[TrafficRecordResponse]:
    return list_mongo_records(collection, limit=limit, offset=offset)


@mongo_router.get(
    "/{source_row}",
    response_model=TrafficRecordResponse,
    summary="Get a single traffic record by source_row from MongoDB",
)
def mongo_get_record(
    source_row: int,
    collection: Collection[dict[str, Any]] = Depends(get_mongo_collection),
) -> TrafficRecordResponse:
    return get_mongo_record_by_source_row(collection, source_row)


@mongo_router.put(
    "/{source_row}",
    response_model=TrafficRecordResponse,
    summary="Update a traffic record by source_row in MongoDB",
)
def mongo_update_record(
    source_row: int,
    payload: TrafficRecordUpdate,
    collection: Collection[dict[str, Any]] = Depends(get_mongo_collection),
) -> TrafficRecordResponse:
    return update_mongo_record(collection, source_row, payload)


@mongo_router.delete(
    "/{source_row}",
    response_model=DeleteRecordResponse,
    summary="Delete a traffic record by source_row from MongoDB",
)
def mongo_delete_record(
    source_row: int,
    collection: Collection[dict[str, Any]] = Depends(get_mongo_collection),
) -> DeleteRecordResponse:
    return delete_mongo_record(collection, source_row)


app.include_router(sql_router)
app.include_router(mongo_router)


@app.get("/", tags=["Service Info"])
def root() -> dict[str, Any]:
    """Return service overview and endpoint summary."""
    return {
        "service": "Metro Interstate Traffic Time-Series API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "sql": {
                "create": "POST /api/sql/records",
                "latest": "GET /api/sql/records/latest",
                "recent": "GET /api/sql/records/recent?limit=25",
                "date_range": "GET /api/sql/records/date-range?start=...&end=...",
                "list": "GET /api/sql/records",
                "get_by_id": "GET /api/sql/records/{source_row}",
                "update": "PUT /api/sql/records/{source_row}",
                "delete": "DELETE /api/sql/records/{source_row}",
            },
            "mongodb": {
                "create": "POST /api/mongodb/records",
                "latest": "GET /api/mongodb/records/latest",
                "recent": "GET /api/mongodb/records/recent?limit=25",
                "date_range": "GET /api/mongodb/records/date-range?start=...&end=...",
                "list": "GET /api/mongodb/records",
                "get_by_id": "GET /api/mongodb/records/{source_row}",
                "update": "PUT /api/mongodb/records/{source_row}",
                "delete": "DELETE /api/mongodb/records/{source_row}",
            },
        },
    }


@app.get("/health", tags=["Service Info"])
def health() -> dict[str, str]:
    """Return basic API health status."""
    return {"status": "ok"}
