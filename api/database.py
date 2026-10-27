"""Database connection configuration and FastAPI dependencies for MySQL and MongoDB."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import mysql.connector
from fastapi import HTTPException, status
from pymongo import MongoClient
from pymongo.collection import Collection

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_dotenv_if_present(dotenv_path: Path | None = None) -> None:
    """Load environment variables from a local .env file if present."""
    path = dotenv_path or (PROJECT_ROOT / ".env")
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def get_mysql_config() -> dict[str, Any]:
    """Build the MySQL connector configuration dictionary from environment variables."""
    load_dotenv_if_present()

    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD") or os.getenv("MYSQL_ROOT_PASSWORD")
    if not password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "MySQL credentials are not configured. "
                "Set MYSQL_PASSWORD (or MYSQL_ROOT_PASSWORD in .env)."
            ),
        )

    raw_port = os.getenv("MYSQL_PORT") or os.getenv("MYSQL_PORT_HOST", "3306")
    try:
        port = int(raw_port)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MYSQL_PORT must be an integer; got {raw_port!r}",
        ) from error

    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": port,
        "user": user,
        "password": password,
        "database": os.getenv("MYSQL_DATABASE", "time_series_traffic"),
    }


def get_sql_connection() -> Generator[Any, None, None]:
    """FastAPI dependency yielding an active MySQL database connection."""
    config = get_mysql_config()
    try:
        connection = mysql.connector.connect(**config)
    except mysql.connector.Error as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not connect to MySQL database: {error}",
        ) from error

    try:
        yield connection
    finally:
        connection.close()


def get_mongodb_uri() -> str:
    """Resolve the MongoDB connection URI from environment variables."""
    load_dotenv_if_present()

    explicit_uri = os.getenv("MONGODB_URI")
    if explicit_uri:
        return explicit_uri

    username = os.getenv("MONGODB_ROOT_USERNAME", "traffic_admin")
    password = os.getenv("MONGODB_ROOT_PASSWORD")
    host = os.getenv("MONGODB_HOST", "127.0.0.1")
    port = os.getenv("MONGODB_PORT") or os.getenv("MONGODB_PORT_HOST", "27017")

    if password:
        encoded_user = quote_plus(username)
        encoded_pass = quote_plus(password)
        return f"mongodb://{encoded_user}:{encoded_pass}@{host}:{port}/?authSource=admin"

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "MongoDB connection is not configured. "
            "Set MONGODB_URI (or MONGODB_ROOT_PASSWORD in .env)."
        ),
    )


def get_mongo_collection() -> Generator[Collection[dict[str, Any]], None, None]:
    """FastAPI dependency yielding the MongoDB traffic_observations collection."""
    uri = get_mongodb_uri()
    database_name = os.getenv("MONGODB_DATABASE", "time_series_traffic")
    collection_name = os.getenv("MONGODB_COLLECTION", "traffic_observations")

    client: MongoClient[dict[str, Any]] = MongoClient(
        uri,
        serverSelectionTimeoutMS=5000,
    )
    try:
        yield client[database_name][collection_name]
    finally:
        client.close()
