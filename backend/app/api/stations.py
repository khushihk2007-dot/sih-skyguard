"""
The Witness Network – Station API Routes
==========================================
Endpoints for querying weather station metadata, historical
readings, and prediction statistics.

GET /api/stations                       → List all known stations
GET /api/stations/{station_id}/readings → Historical readings
GET /api/stations/{station_id}/stats    → Summary statistics
GET /api/stations/{station_id}/predict  → Current prediction
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.sensor_data import (
    DataSource,
    SensorReading,
    SensorReadingResponse,
)
from app.services.prediction_service import predict_temperature, get_station_stats


router = APIRouter(prefix="/api/stations", tags=["Stations"])


# ── GET /api/stations ────────────────────────────────────────────────

@router.get(
    "",
    summary="List all known stations",
    description="Returns a unique list of all station IDs that have sent data.",
)
async def list_stations(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return all distinct station IDs and their reading counts."""
    stmt = (
        select(
            SensorReading.station_id,
            func.count(SensorReading.id).label("total_readings"),
            func.max(SensorReading.received_at).label("last_seen"),
        )
        .group_by(SensorReading.station_id)
        .order_by(SensorReading.station_id)
    )
    result = await db.execute(stmt)
    rows = result.fetchall()

    stations = [
        {
            "station_id": row.station_id,
            "total_readings": row.total_readings,
            "last_seen": row.last_seen.isoformat() if row.last_seen else None,
        }
        for row in rows
    ]

    return {"count": len(stations), "stations": stations}


# ── GET /api/stations/{station_id}/readings ──────────────────────────

@router.get(
    "/{station_id}/readings",
    response_model=dict,
    summary="Get historical readings for a station",
)
async def get_station_readings(
    station_id: str,
    source: Optional[DataSource] = Query(
        None, description="Filter by data source (AWS or WITNESS)"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retrieve paginated historical readings for a specific station."""
    stmt = (
        select(SensorReading)
        .where(SensorReading.station_id == station_id)
        .order_by(SensorReading.received_at.desc())
    )

    if source:
        stmt = stmt.where(SensorReading.source == source)

    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    readings = result.scalars().all()

    return {
        "station_id": station_id,
        "count": len(readings),
        "readings": [
            SensorReadingResponse.model_validate(r).model_dump()
            for r in readings
        ],
    }


# ── GET /api/stations/{station_id}/stats ─────────────────────────────

@router.get(
    "/{station_id}/stats",
    summary="Get summary statistics for a station",
)
async def get_stats(
    station_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return count, mean, min, max temperature for a station."""
    stats = await get_station_stats(station_id, db)
    return stats


# ── GET /api/stations/{station_id}/predict ───────────────────────────

@router.get(
    "/{station_id}/predict",
    summary="Get current temperature prediction",
    description=(
        "Returns the ML-predicted baseline temperature for the station "
        "based on a rolling window of recent historical readings."
    ),
)
async def get_prediction(
    station_id: str,
    window_size: Optional[int] = Query(
        None, ge=2, le=100,
        description="Number of recent readings to average over",
    ),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate and return the predicted temperature for a station."""
    predicted = await predict_temperature(station_id, db, window_size)
    return {
        "station_id": station_id,
        "t_predicted": predicted,
        "window_size": window_size or "default",
    }
