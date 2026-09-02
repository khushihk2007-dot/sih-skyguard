"""
The Witness Network – Prediction Service
==========================================
Generates a predicted baseline temperature (T_Predicted) for a
given station using a rolling-window average of recent historical
readings.

This is the "third voice" in the Three-Way Arbitration:
    T_AWS  vs  T_Witness  vs  T_Predicted

In production, this can be swapped out for an LSTM / Prophet model
by replacing `predict_temperature()` with a model inference call.
"""

from typing import Optional

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.sensor_data import SensorReading


async def predict_temperature(
    station_id: str,
    db: AsyncSession,
    window_size: Optional[int] = None,
) -> float:
    """
    Generate a predicted temperature for the given station.

    Strategy (v1 – rolling mean):
        Compute the mean temperature of the last `window_size` readings
        for the station, regardless of source. This serves as a simple
        but effective baseline until a trained ML model is deployed.

    Parameters:
        station_id  – Station to predict for.
        db          – Active async database session.
        window_size – Number of recent readings to average over.
                      Defaults to settings.PREDICTION_WINDOW_SIZE.

    Returns:
        Predicted temperature in °C.  Falls back to 25.0°C if no
        historical data is available (cold-start scenario).
    """
    window: int = window_size or settings.PREDICTION_WINDOW_SIZE

    # Fetch the most recent `window` readings for this station
    stmt = (
        select(SensorReading.temperature)
        .where(SensorReading.station_id == station_id)
        .order_by(SensorReading.received_at.desc())
        .limit(window)
    )
    result = await db.execute(stmt)
    temps: list[float] = [row[0] for row in result.fetchall()]

    if not temps:
        # Cold-start: no historical data available for this station
        logger.warning(
            f"[Predict] No historical data for station={station_id}. "
            f"Returning default prediction of 25.0°C."
        )
        return 25.0

    predicted: float = sum(temps) / len(temps)

    logger.debug(
        f"[Predict] station={station_id} | window={len(temps)} readings | "
        f"T_predicted={predicted:.2f}°C"
    )
    return round(predicted, 2)


async def get_station_stats(
    station_id: str,
    db: AsyncSession,
) -> dict:
    """
    Return summary statistics for a station's historical readings.

    Returns:
        Dict with keys: count, mean, min, max.
    """
    stmt = select(
        func.count(SensorReading.id).label("count"),
        func.avg(SensorReading.temperature).label("mean"),
        func.min(SensorReading.temperature).label("min"),
        func.max(SensorReading.temperature).label("max"),
    ).where(SensorReading.station_id == station_id)

    result = await db.execute(stmt)
    row = result.one()

    return {
        "station_id": station_id,
        "reading_count": row.count or 0,
        "mean_temperature": round(row.mean, 2) if row.mean else None,
        "min_temperature": row.min,
        "max_temperature": row.max,
    }
