"""
The Witness Network – Station Models
======================================
SQLAlchemy ORM model and Pydantic schemas for the Station registry.
Each station represents a physical IMD/AWS weather observation point.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Float, String

from app.core.database import Base


# ── SQLAlchemy ORM Model ─────────────────────────────────────────────

class Station(Base):
    """
    Registry entry for a physical weather station.

    Attributes:
        id:          Unique station identifier (e.g. "AWS-DEL-001").
        name:        Human-readable station name (e.g. "New Delhi – Safdarjung").
        latitude:    Geographic latitude in decimal degrees.
        longitude:   Geographic longitude in decimal degrees.
        created_at:  Timestamp when this station was registered.
    """

    __tablename__ = "stations"

    id: str = Column(
        String(64), primary_key=True, nullable=False,
        comment="Unique station identifier, e.g. AWS-DEL-001",
    )
    name: str = Column(String(128), nullable=False)
    latitude: float = Column(Float, nullable=False)
    longitude: float = Column(Float, nullable=False)
    created_at: datetime = Column(
        DateTime, nullable=False, default=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return (
            f"<Station id={self.id} name={self.name!r} "
            f"({self.latitude}, {self.longitude})>"
        )


# ── Pydantic Schemas ─────────────────────────────────────────────────

class StationResponse(BaseModel):
    """Schema returned when listing registered stations."""

    station_id: str = Field(..., description="Unique station identifier")
    name: str = Field(..., description="Human-readable station name")
    latitude: float = Field(..., description="Latitude in decimal degrees")
    longitude: float = Field(..., description="Longitude in decimal degrees")
    created_at: datetime

    class Config:
        from_attributes = True


class StationStatusResponse(BaseModel):
    """
    Live status for a single station.

    Merges the station registry data with the most recent
    AnomalyEvent arbitration result for that station.
    """

    station_id: str = Field(..., description="Unique station identifier")
    name: str = Field(..., description="Human-readable station name")
    latitude: float
    longitude: float

    # Latest arbitration result (defaults if no data yet)
    decision: str = Field(
        default="NORMAL",
        description="Latest arbitration decision: PRIMARY_DRIFT / WITNESS_FAULT / TRUE_EXTREME / NORMAL",
    )
    severity: str = Field(
        default="LOW",
        description="Severity of the latest anomaly event",
    )
    t_aws: Optional[float] = Field(
        None, description="AWS temperature from latest event (°C)",
    )
    t_witness: Optional[float] = Field(
        None, description="Witness temperature from latest event (°C)",
    )
    t_predicted: Optional[float] = Field(
        None, description="Predicted temperature from latest event (°C)",
    )
    neighbours_used: Optional[int] = Field(
        None, description="Number of neighbouring stations used for IDW spatial prediction",
    )
    is_imputed: bool = Field(
        default=False, description="Whether temperature was imputed (true for PRIMARY_DRIFT)",
    )
    t_imputed: Optional[float] = Field(
        None, description="Imputed temperature value (°C) when is_imputed is True",
    )
    original_t_aws: Optional[float] = Field(
        None, description="Original raw AWS temperature reading before imputation (°C)",
    )
    reason: Optional[str] = Field(
        None, description="Arbitration reason string",
    )
    last_updated: Optional[datetime] = Field(
        None, description="Timestamp of the latest anomaly event (null if no data)",
    )

    class Config:
        from_attributes = True
