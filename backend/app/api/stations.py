"""
The Witness Network – Station API Routes
==========================================
Endpoints for querying weather station metadata, historical
readings, and prediction statistics.

GET /api/stations                       → List all registered stations
GET /api/stations/status                → Live status for every station
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
from app.models.station import Station, StationResponse, StationStatusResponse
from app.models.anomaly import AnomalyEvent, AnomalyDecision
from app.services.prediction_service import predict_temperature, get_station_stats


router = APIRouter(prefix="/api/stations", tags=["Stations"])


# ── GET /api/stations ────────────────────────────────────────────────

@router.get(
    "",
    summary="List all registered stations",
    description=(
        "Returns every station in the registry with its coordinates "
        "and registration timestamp."
    ),
)
async def list_stations(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Return all registered stations from the Station table.
    Each entry includes station_id, name, latitude, longitude, and created_at.
    """
    stmt = select(Station).order_by(Station.id)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    stations = [
        StationResponse(
            station_id=row.id,
            name=row.name,
            latitude=row.latitude,
            longitude=row.longitude,
            created_at=row.created_at,
        ).model_dump()
        for row in rows
    ]

    return {"count": len(stations), "stations": stations}


# ── GET /api/stations/status ─────────────────────────────────────────
# IMPORTANT: This must be registered BEFORE the /{station_id} routes,
# otherwise FastAPI would try to match "status" as a station_id.

@router.get(
    "/status",
    response_model=list[StationStatusResponse],
    summary="Live status for every station",
    description=(
        "Returns one entry per registered station, enriched with "
        "the most recent AnomalyEvent arbitration result. Stations "
        "that have no anomaly data yet default to NORMAL / LOW."
    ),
)
async def station_status(
    db: AsyncSession = Depends(get_db),
) -> list[StationStatusResponse]:
    """
    For each station in the registry, look up the most recent
    AnomalyEvent row (ordered by detected_at DESC, LIMIT 1).
    If no event exists, return safe defaults.
    """
    # 1. Fetch all registered stations
    stmt_stations = select(Station).order_by(Station.id)
    result_stations = await db.execute(stmt_stations)
    stations: list[Station] = list(result_stations.scalars().all())

    # 2. For each station, find the latest anomaly event (if any)
    responses: list[StationStatusResponse] = []

    for station in stations:
        # Sub-query: latest AnomalyEvent for this station_id
        stmt_event = (
            select(AnomalyEvent)
            .where(AnomalyEvent.station_id == station.id)
            .order_by(AnomalyEvent.detected_at.desc())
            .limit(1)
        )
        result_event = await db.execute(stmt_event)
        latest_event: Optional[AnomalyEvent] = result_event.scalar_one_or_none()

        if latest_event is not None:
            # Determine decision string (enum or str)
            dec_str = (
                latest_event.decision.value
                if hasattr(latest_event.decision, "value")
                else str(latest_event.decision)
            )

            # Check if decision is PRIMARY_DRIFT
            is_primary_drift = (dec_str == "PRIMARY_DRIFT" or dec_str == AnomalyDecision.PRIMARY_DRIFT)

            # Resolve is_imputed
            raw_is_imputed = getattr(latest_event, "is_imputed", False)
            is_imputed = True if (raw_is_imputed or is_primary_drift) else False

            # Resolve t_imputed
            raw_t_imputed = getattr(latest_event, "t_imputed", None)
            if is_imputed:
                if raw_t_imputed is not None:
                    t_imputed = raw_t_imputed
                elif latest_event.t_witness is not None and latest_event.t_predicted is not None:
                    # Calculate on the fly if missing from older DB record
                    t_imputed = round((0.6 * latest_event.t_witness) + (0.4 * latest_event.t_predicted), 2)
                else:
                    t_imputed = None
            else:
                t_imputed = None

            # Resolve original_t_aws (fall back to t_aws if original_t_aws is None)
            raw_original_t_aws = getattr(latest_event, "original_t_aws", None)
            original_t_aws = raw_original_t_aws if raw_original_t_aws is not None else latest_event.t_aws

            # Resolve neighbours_used
            raw_neighbours_used = getattr(latest_event, "neighbours_used", None)
            if raw_neighbours_used is not None:
                neighbours_used = raw_neighbours_used
            else:
                _, neighbours_used = await predict_temperature(station.id, db)

            # Station has at least one anomaly event – use its data
            responses.append(
                StationStatusResponse(
                    station_id=station.id,
                    name=station.name,
                    latitude=station.latitude,
                    longitude=station.longitude,
                    decision=dec_str,
                    severity=str(latest_event.severity.value) if hasattr(latest_event.severity, "value") else str(latest_event.severity),
                    t_aws=latest_event.t_aws,
                    t_witness=latest_event.t_witness,
                    t_predicted=latest_event.t_predicted,
                    neighbours_used=neighbours_used,
                    is_imputed=is_imputed,
                    t_imputed=t_imputed,
                    original_t_aws=original_t_aws,
                    reason=latest_event.reason,
                    last_updated=latest_event.detected_at,
                )
            )
        else:
            # No anomaly data yet – return defaults
            _, neighbours_used = await predict_temperature(station.id, db)
            responses.append(
                StationStatusResponse(
                    station_id=station.id,
                    name=station.name,
                    latitude=station.latitude,
                    longitude=station.longitude,
                    decision="NORMAL",
                    severity="LOW",
                    t_aws=None,
                    t_witness=None,
                    t_predicted=None,
                    neighbours_used=neighbours_used,
                    is_imputed=False,
                    t_imputed=None,
                    original_t_aws=None,
                    reason=None,
                    last_updated=None,
                )
            )

    return responses


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
    predicted, neighbours_used = await predict_temperature(station_id, db, window_size)
    return {
        "station_id": station_id,
        "t_predicted": predicted,
        "neighbours_used": neighbours_used,
        "window_size": window_size or "default",
    }
