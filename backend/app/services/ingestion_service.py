"""
The Witness Network – Ingestion Service
=========================================
Business logic for persisting incoming sensor readings from
both Stream A (AWS) and Stream B (Witness Nodes).

After persisting, the service checks if both streams have fresh
data for the same station and triggers the arbitration engine
automatically.
"""

from datetime import datetime, timedelta
from typing import Optional

from loguru import logger
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sensor_data import (
    DataSource,
    SensorReading,
    SensorReadingCreate,
    SensorReadingResponse,
)
from app.models.anomaly import ArbitrationResponse
from app.services.anomaly_engine import run_arbitration
from app.services.prediction_service import predict_temperature
from app.services.thermodynamic_service import (
    check_thermodynamic_consistency,
    ConsistencyVerdict,
)


# ── Maximum age of a paired reading for auto-arbitration (seconds) ──
PAIRING_WINDOW_SECONDS: int = 300  # 5 minutes


async def ingest_reading(
    payload: SensorReadingCreate,
    db: AsyncSession,
) -> tuple[SensorReadingResponse, Optional[ArbitrationResponse]]:
    """
    Persist a single sensor reading and optionally trigger arbitration.

    Workflow:
        1. Save the incoming reading to the database.
        2. **Layer 1** – Run the Thermodynamic Consistency Gate on the
           incoming reading.  If it FAILs, skip arbitration.
        3. Look for a recent counterpart reading from the other stream.
        4. Run the thermodynamic gate on the counterpart as well.
        5. If both readings pass, generate a prediction and run
           Three-Way Arbitration (Layer 2).

    Parameters:
        payload – Validated sensor reading data.
        db      – Active async database session.

    Returns:
        Tuple of (saved reading response, optional arbitration result).
    """
    # ── Step 1: Persist the reading ───────────────────────────────
    reading = SensorReading(
        station_id=payload.station_id,
        source=payload.source,
        temperature=payload.temperature,
        humidity=payload.humidity,
        pressure=payload.pressure,
        recorded_at=payload.recorded_at,
        received_at=datetime.utcnow(),
    )
    db.add(reading)
    await db.commit()
    await db.refresh(reading)

    logger.info(
        f"[Ingest] Saved {payload.source.value} reading for "
        f"station={payload.station_id}: T={payload.temperature}°C"
    )

    reading_response = SensorReadingResponse.model_validate(reading)

    # ── Step 2 (Layer 1): Thermodynamic Consistency Gate ──────────
    if payload.humidity is not None:
        thermo_result = await check_thermodynamic_consistency(
            temperature=payload.temperature,
            humidity=payload.humidity,
            pressure=payload.pressure,
        )
        if thermo_result["verdict"] == ConsistencyVerdict.FAIL.value:
            logger.warning(
                f"[Ingest] Thermodynamic gate FAILED for incoming "
                f"{payload.source.value} reading at "
                f"station={payload.station_id} — skipping arbitration. "
                f"Flags: {thermo_result['flags']}"
            )
            return reading_response, None

    # ── Step 3: Try to find a matching counterpart ────────────────
    other_source = (
        DataSource.WITNESS
        if payload.source == DataSource.AWS
        else DataSource.AWS
    )
    cutoff = datetime.utcnow() - timedelta(seconds=PAIRING_WINDOW_SECONDS)

    stmt = (
        select(SensorReading)
        .where(
            and_(
                SensorReading.station_id == payload.station_id,
                SensorReading.source == other_source,
                SensorReading.received_at >= cutoff,
            )
        )
        .order_by(SensorReading.received_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    counterpart: Optional[SensorReading] = result.scalar_one_or_none()

    if counterpart is None:
        logger.debug(
            f"[Ingest] No recent {other_source.value} reading for "
            f"station={payload.station_id} – skipping arbitration"
        )
        return reading_response, None

    # ── Step 4 (Layer 1): Thermodynamic gate on counterpart ───────
    if counterpart.humidity is not None:
        counter_thermo = await check_thermodynamic_consistency(
            temperature=counterpart.temperature,
            humidity=counterpart.humidity,
            pressure=counterpart.pressure,
        )
        if counter_thermo["verdict"] == ConsistencyVerdict.FAIL.value:
            logger.warning(
                f"[Ingest] Thermodynamic gate FAILED for counterpart "
                f"{other_source.value} reading at "
                f"station={payload.station_id} — skipping arbitration. "
                f"Flags: {counter_thermo['flags']}"
            )
            return reading_response, None

    # ── Step 5: Determine T_AWS and T_Witness ─────────────────────
    if payload.source == DataSource.AWS:
        t_aws = payload.temperature
        t_witness = counterpart.temperature
    else:
        t_aws = counterpart.temperature
        t_witness = payload.temperature

    # ── Step 6 (Layer 2): Generate prediction & run arbitration ───
    t_predicted: float = await predict_temperature(
        station_id=payload.station_id, db=db
    )

    arbitration_result = await run_arbitration(
        station_id=payload.station_id,
        t_aws=t_aws,
        t_witness=t_witness,
        t_predicted=t_predicted,
        db=db,
    )

    return reading_response, arbitration_result


async def ingest_bulk(
    readings: list[SensorReadingCreate],
    db: AsyncSession,
) -> list[SensorReadingResponse]:
    """
    Persist a batch of sensor readings without triggering individual
    arbitrations (use for historical data backfill).

    Parameters:
        readings – List of validated sensor readings.
        db       – Active async database session.

    Returns:
        List of saved reading responses.
    """
    orm_objects = [
        SensorReading(
            station_id=r.station_id,
            source=r.source,
            temperature=r.temperature,
            humidity=r.humidity,
            pressure=r.pressure,
            recorded_at=r.recorded_at,
            received_at=datetime.utcnow(),
        )
        for r in readings
    ]

    db.add_all(orm_objects)
    await db.commit()

    # Refresh all to get generated IDs
    for obj in orm_objects:
        await db.refresh(obj)

    logger.info(f"[Ingest] Bulk-inserted {len(orm_objects)} readings")

    return [SensorReadingResponse.model_validate(obj) for obj in orm_objects]
