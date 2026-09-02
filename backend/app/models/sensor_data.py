"""
The Witness Network – Sensor Data Models
==========================================
SQLAlchemy ORM models and Pydantic schemas for weather sensor
readings from both Stream A (AWS) and Stream B (Witness Nodes).
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Enum as SAEnum,
)
from app.core.database import Base


# ── Enums ─────────────────────────────────────────────────────────────

class DataSource(str, Enum):
    """Identifies which data stream a reading came from."""
    AWS = "AWS"               # Stream A – Official AWS weather station
    WITNESS = "WITNESS"       # Stream B – ESP32 + BME280 edge node


# ── SQLAlchemy ORM Model ─────────────────────────────────────────────

class SensorReading(Base):
    """
    Persistent record of a single temperature observation.

    Attributes:
        id:             Auto-incrementing primary key.
        station_id:     Unique identifier of the weather station / node.
        source:         Which data stream produced this reading.
        temperature:    Observed temperature in °C.
        humidity:       Relative humidity in % (optional, witness nodes).
        pressure:       Atmospheric pressure in hPa (optional).
        recorded_at:    Timestamp of the observation at the source.
        received_at:    Timestamp when the backend received the reading.
    """

    __tablename__ = "sensor_readings"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    station_id: str = Column(String(64), nullable=False, index=True)
    source: str = Column(SAEnum(DataSource), nullable=False, index=True)
    temperature: float = Column(Float, nullable=False)
    humidity: Optional[float] = Column(Float, nullable=True)
    pressure: Optional[float] = Column(Float, nullable=True)
    recorded_at: datetime = Column(DateTime, nullable=False)
    received_at: datetime = Column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return (
            f"<SensorReading station={self.station_id} src={self.source} "
            f"T={self.temperature}°C @ {self.recorded_at}>"
        )


# ── Pydantic Schemas (Request / Response) ─────────────────────────────

class SensorReadingCreate(BaseModel):
    """Schema for ingesting a new sensor reading via the REST API."""

    station_id: str = Field(
        ..., min_length=1, max_length=64,
        description="Unique identifier of the station or witness node",
        examples=["AWS-MUM-001", "WN-BLR-042"],
    )
    source: DataSource = Field(
        ..., description="Data stream origin (AWS or WITNESS)"
    )
    temperature: float = Field(
        ..., ge=-60.0, le=60.0,
        description="Temperature in °C (sanity-clamped)",
        examples=[32.5],
    )
    humidity: Optional[float] = Field(
        None, ge=0.0, le=100.0,
        description="Relative humidity in %",
    )
    pressure: Optional[float] = Field(
        None, ge=800.0, le=1200.0,
        description="Atmospheric pressure in hPa",
    )
    recorded_at: datetime = Field(
        ..., description="ISO-8601 timestamp of the observation"
    )


class SensorReadingResponse(BaseModel):
    """Schema returned after successfully persisting a reading."""

    id: int
    station_id: str
    source: DataSource
    temperature: float
    humidity: Optional[float]
    pressure: Optional[float]
    recorded_at: datetime
    received_at: datetime

    class Config:
        from_attributes = True


class BulkIngestRequest(BaseModel):
    """Accept multiple readings in a single API call."""
    readings: list[SensorReadingCreate] = Field(
        ..., min_length=1, max_length=500,
        description="Batch of sensor readings (max 500 per call)",
    )
