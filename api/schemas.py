"""Pydantic schemas for traffic time-series CRUD and query endpoints."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

NULL_STRINGS = {"", "nan", "none", "null"}


def normalize_optional_text(value: Any) -> str | None:
    """Convert empty or sentinel strings ('None', 'null', 'nan') to None."""
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in NULL_STRINGS:
        return None
    return text


def parse_naive_datetime(value: Any) -> datetime:
    """Parse an ISO timestamp string or datetime into a timezone-naive datetime."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("date_time cannot be empty")
        try:
            dt = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(
                f"Invalid ISO datetime format: {value!r}. "
                "Expected format like '2018-09-30T23:00:00' or '2018-09-30 23:00:00'."
            ) from error
    else:
        raise ValueError(f"date_time must be a datetime or ISO string; got {type(value).__name__}")

    # Store and query as naive wall-clock timestamps to match Task 2 conventions
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt


class WeatherObservation(BaseModel):
    """Weather measurements associated with a traffic observation."""

    model_config = ConfigDict(extra="forbid")

    temp: float | None = Field(
        default=None,
        description="Temperature in Kelvin (e.g., 288.28)",
    )
    rain_1h: float | None = Field(
        default=0.0,
        ge=0.0,
        description="Rain in mm for the hour",
    )
    snow_1h: float | None = Field(
        default=0.0,
        ge=0.0,
        description="Snow in mm for the hour",
    )
    clouds_all: float | None = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Cloud coverage percentage (0 to 100)",
    )
    weather_main: str | None = Field(
        default=None,
        max_length=50,
        description="Short weather category (e.g., 'Clouds', 'Clear', 'Rain')",
    )
    weather_description: str | None = Field(
        default=None,
        max_length=255,
        description="Detailed weather description (e.g., 'scattered clouds')",
    )

    @field_validator("temp", "rain_1h", "snow_1h", "clouds_all")
    @classmethod
    def validate_finite_number(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("Numeric weather values must be finite")
        return value

    @field_validator("weather_main", "weather_description", mode="before")
    @classmethod
    def clean_text_fields(cls, value: Any) -> str | None:
        return normalize_optional_text(value)


def _group_flat_weather_fields(data: Any) -> Any:
    """Allow callers to supply weather fields either nested under 'weather' or flat."""
    if not isinstance(data, dict):
        return data
    weather_keys = (
        "temp",
        "rain_1h",
        "snow_1h",
        "clouds_all",
        "weather_main",
        "weather_description",
    )
    if "weather" not in data and any(key in data for key in weather_keys):
        copied = dict(data)
        weather_dict = {}
        for key in weather_keys:
            if key in copied:
                weather_dict[key] = copied.pop(key)
        copied["weather"] = weather_dict
        return copied
    return data


class TrafficRecordCreate(BaseModel):
    """Payload for creating a new traffic observation (POST)."""

    model_config = ConfigDict(extra="forbid")

    source_row: int | None = Field(
        default=None,
        ge=1,
        description="Optional unique source row identifier. Auto-assigned if omitted.",
    )
    date_time: datetime = Field(
        ...,
        description="Observation timestamp (ISO-8601 format, e.g., '2018-10-01T00:00:00')",
    )
    traffic_volume: int = Field(
        ...,
        ge=0,
        description="Hourly interstate traffic volume (non-negative integer)",
    )
    holiday: str | None = Field(
        default=None,
        max_length=100,
        description="Holiday name if observed on a holiday, or null/None",
    )
    weather: WeatherObservation = Field(
        default_factory=WeatherObservation,
        description="Associated hourly weather measurements",
    )

    @model_validator(mode="before")
    @classmethod
    def support_flat_weather(cls, data: Any) -> Any:
        return _group_flat_weather_fields(data)

    @field_validator("date_time", mode="before")
    @classmethod
    def validate_date_time(cls, value: Any) -> datetime:
        return parse_naive_datetime(value)

    @field_validator("holiday", mode="before")
    @classmethod
    def validate_holiday(cls, value: Any) -> str | None:
        return normalize_optional_text(value)


class TrafficRecordUpdate(BaseModel):
    """Payload for updating an existing traffic observation (PUT)."""

    model_config = ConfigDict(extra="forbid")

    date_time: datetime | None = Field(
        default=None,
        description="Updated observation timestamp",
    )
    traffic_volume: int | None = Field(
        default=None,
        ge=0,
        description="Updated hourly traffic volume",
    )
    holiday: str | None = Field(
        default=None,
        max_length=100,
        description="Updated holiday name (or 'None'/null to clear holiday)",
    )
    weather: WeatherObservation | None = Field(
        default=None,
        description="Updated weather observation fields",
    )

    @model_validator(mode="before")
    @classmethod
    def support_flat_weather(cls, data: Any) -> Any:
        return _group_flat_weather_fields(data)

    @field_validator("date_time", mode="before")
    @classmethod
    def validate_date_time(cls, value: Any) -> datetime | None:
        if value is None:
            return None
        return parse_naive_datetime(value)

    @field_validator("holiday", mode="before")
    @classmethod
    def validate_holiday(cls, value: Any) -> str | None:
        return normalize_optional_text(value)


class TrafficRecordResponse(BaseModel):
    """Standardized response model returned by both SQL and MongoDB endpoints."""

    source_row: int = Field(..., description="Unique observation row identifier")
    date_time: datetime = Field(..., description="Observation timestamp")
    traffic_volume: int = Field(..., description="Hourly interstate traffic volume")
    holiday: str | None = Field(default=None, description="Holiday label or null")
    weather: WeatherObservation = Field(..., description="Weather measurements")


class DeleteRecordResponse(BaseModel):
    """Response returned when a record is deleted."""

    database: str
    source_row: int
    deleted: bool
    message: str
