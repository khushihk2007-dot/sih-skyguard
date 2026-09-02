"""
The Witness Network – Ingestion API Routes
============================================
REST endpoints for receiving weather data from:
  • Stream A – Official AWS temperature observations
  • Stream B – ESP32 + BME280 Witness Node readings

POST /api/ingest          → Single reading (auto-triggers arbitration)
POST /api/ingest/bulk     → Batch import (no auto-arbitration)
POST /api/ingest/arbitrate → Manual ad-hoc arbitration
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.sensor_data import (
    BulkIngestRequest,
    SensorReadingCreate,
    SensorReadingResponse,
)
from app.models.anomaly import (
    ArbitrationRequest,
    ArbitrationResponse,
)
from app.services.ingestion_service import ingest_reading, ingest_bulk
from app.services.anomaly_engine import run_arbitration
from app.services.prediction_service import predict_temperature


router = APIRouter(prefix="/api/ingest", tags=["Ingestion"])


# ── POST /api/ingest ─────────────────────────────────────────────────

@router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a single sensor reading",
    description=(
        "Accepts a temperature reading from either Stream A (AWS) or "
        "Stream B (Witness). If a matching reading from the other stream "
        "is found within the pairing window, arbitration runs automatically."
    ),
)
async def ingest_single(
    payload: SensorReadingCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Ingest one reading and optionally trigger Three-Way Arbitration."""
    reading, arbitration = await ingest_reading(payload, db)

    response: dict = {
        "status": "ingested",
        "reading": reading.model_dump(),
    }

    if arbitration is not None:
        response["arbitration"] = arbitration.model_dump()
        response["status"] = "ingested_with_arbitration"

    return response


# ── POST /api/ingest/bulk ────────────────────────────────────────────

@router.post(
    "/bulk",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Bulk-ingest sensor readings",
    description=(
        "Accepts up to 500 readings in a single call. Useful for "
        "historical data backfill. Arbitration is NOT auto-triggered."
    ),
)
async def ingest_batch(
    payload: BulkIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Bulk-insert readings without triggering arbitration."""
    readings = await ingest_bulk(payload.readings, db)
    return {
        "status": "bulk_ingested",
        "count": len(readings),
        "readings": [r.model_dump() for r in readings],
    }


# ── POST /api/ingest/arbitrate ───────────────────────────────────────

@router.post(
    "/arbitrate",
    response_model=ArbitrationResponse,
    summary="Run manual Three-Way Arbitration",
    description=(
        "Provide T_AWS, T_Witness, and optionally T_Predicted to run "
        "a one-off arbitration evaluation. The result is persisted as "
        "an anomaly event. If T_Predicted is omitted, the prediction "
        "service generates one from historical data."
    ),
)
async def manual_arbitration(
    payload: ArbitrationRequest,
    db: AsyncSession = Depends(get_db),
) -> ArbitrationResponse:
    """Execute an ad-hoc arbitration and persist the result."""
    # Resolve T_Predicted if not provided
    t_predicted: float = payload.t_predicted or await predict_temperature(
        station_id=payload.station_id, db=db
    )

    result = await run_arbitration(
        station_id=payload.station_id,
        t_aws=payload.t_aws,
        t_witness=payload.t_witness,
        t_predicted=t_predicted,
        db=db,
        epsilon=payload.epsilon,
        delta=payload.delta,
    )
    return result
