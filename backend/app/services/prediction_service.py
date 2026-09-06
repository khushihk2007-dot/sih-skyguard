"""
The Witness Network – Prediction Service (v2 – Spatial IDW)
============================================================
Generates a predicted baseline temperature (T_Predicted) for a
given station using **Inverse Distance Weighting (IDW)** over
neighbouring stations within a configurable radius.

Strategy:
    1. Load all registered stations with their coordinates.
    2. Compute the Haversine great-circle distance from the target
       station to every other station.
    3. Select neighbours within SPATIAL_RADIUS_KM (default 50 km).
    4. For each neighbour, compute the mean of its last
       PREDICTION_WINDOW_SIZE readings as a representative temperature.
    5. Combine neighbour temperatures using IDW:
           T_predicted = Σ(T_i / d_i^p) / Σ(1 / d_i^p)
       where p = IDW_POWER (default 2) and d_i is the distance in km.
    6. If no neighbours exist within the radius, fall back to the
       station's own recent average (rolling mean).
    7. If no historical data at all (cold-start), return a hard
       coded regional default.

This is the "third voice" in the Three-Way Arbitration:
    T_AWS  vs  T_Witness  vs  T_Predicted

The spatial awareness makes T_Predicted much harder to fool — a
faulty AWS reading at Delhi won't be "confirmed" by a prediction
that was itself derived from the same faulty station's history.
"""

import math
from typing import Optional

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.sensor_data import SensorReading
from app.models.station import Station


# ── Tunable spatial parameters ────────────────────────────────────────

SPATIAL_RADIUS_KM: float = 500.0
"""Maximum great-circle distance (km) to include a neighbour in IDW.
   Set to 500 km for India's 12-station network so that every station
   always has at least one or two valid neighbours. For denser networks
   this can be tightened to 50–100 km."""

IDW_POWER: float = 2.0
"""Exponent p in the IDW formula  w = 1 / d^p.
   Higher p → closer stations dominate more strongly."""

COLD_START_DEFAULT: float = 28.0
"""Fallback temperature (°C) used when a station has no readings AND
   no neighbours.  28°C is the approximate all-India annual mean."""


# ── Haversine formula ─────────────────────────────────────────────────

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Compute the great-circle distance between two points on Earth.

    Uses the Haversine formula which is accurate to within ~0.3% for
    distances up to a few thousand kilometres.

    Parameters:
        lat1, lon1 – Decimal degrees of the first point.
        lat2, lon2 – Decimal degrees of the second point.

    Returns:
        Distance in kilometres.
    """
    EARTH_RADIUS_KM = 6_371.0

    # Convert decimal degrees → radians
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)

    # Haversine central-angle formula
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    return EARTH_RADIUS_KM * c


# ── Per-station recent average (helper) ──────────────────────────────

async def _station_recent_avg(
    station_id: str,
    db: AsyncSession,
    window: int,
) -> Optional[float]:
    """
    Return the mean of the last `window` temperature readings for a
    station, or None if no readings exist.
    """
    stmt = (
        select(func.avg(SensorReading.temperature))
        .where(SensorReading.station_id == station_id)
        .where(
            SensorReading.id.in_(
                select(SensorReading.id)
                .where(SensorReading.station_id == station_id)
                .order_by(SensorReading.received_at.desc())
                .limit(window)
                .scalar_subquery()
            )
        )
    )
    result = await db.execute(stmt)
    avg = result.scalar_one_or_none()
    return round(float(avg), 4) if avg is not None else None


# ── Main prediction function ──────────────────────────────────────────

async def predict_temperature(
    station_id: str,
    db: AsyncSession,
    window_size: Optional[int] = None,
) -> tuple[float, int]:
    """
    Generate a spatially-aware predicted temperature for the given station
    using Inverse Distance Weighting (IDW) over nearby neighbour stations.

    Algorithm
    ---------
    1. Load the target station's coordinates from the registry.
    2. Load all other registered stations.
    3. Compute Haversine distance to each candidate.
    4. Keep candidates within SPATIAL_RADIUS_KM that have at least one
       recent reading (their recent average ≠ None).
    5. Compute IDW:
           weight_i = 1 / distance_i ^ IDW_POWER
           T_pred   = Σ(weight_i × T_i) / Σ(weight_i)
    6. Fallback to the station's own rolling mean if no neighbours.
    7. Fallback to COLD_START_DEFAULT if no data at all.

    Parameters
    ----------
    station_id  : Station to predict for.
    db          : Active async SQLAlchemy session.
    window_size : Recent readings to average per station.
                  Defaults to settings.PREDICTION_WINDOW_SIZE.

    Returns
    -------
    tuple[float, int]
        (predicted_temperature, neighbours_used)
    """
    window: int = window_size or settings.PREDICTION_WINDOW_SIZE

    # ── Step 1: Load target station coordinates ───────────────────────
    stmt_target = select(Station).where(Station.id == station_id)
    result_target = await db.execute(stmt_target)
    target: Optional[Station] = result_target.scalar_one_or_none()

    if target is None:
        logger.warning(
            f"[Predict-IDW] station={station_id} not found in registry. "
            f"Returning cold-start default {COLD_START_DEFAULT}°C."
        )
        return COLD_START_DEFAULT, 0

    # ── Step 2: Load all other registered stations ────────────────────
    stmt_all = select(Station).where(Station.id != station_id)
    result_all = await db.execute(stmt_all)
    all_others: list[Station] = list(result_all.scalars().all())

    # ── Steps 3 & 4: Find neighbours within radius ────────────────────
    # Each entry: (distance_km, mean_temp)
    neighbours: list[tuple[float, float]] = []

    for candidate in all_others:
        dist_km = haversine_km(
            target.latitude, target.longitude,
            candidate.latitude, candidate.longitude,
        )

        if dist_km > SPATIAL_RADIUS_KM:
            continue  # Too far away

        avg_temp = await _station_recent_avg(candidate.id, db, window)

        if avg_temp is None:
            continue  # No readings yet for this neighbour

        neighbours.append((dist_km, avg_temp))
        logger.debug(
            f"[Predict-IDW]   neighbour={candidate.id} "
            f"dist={dist_km:.1f} km  avg_temp={avg_temp:.2f}°C"
        )

    # ── Step 5: Compute IDW if we have neighbours ─────────────────────
    if neighbours:
        weighted_sum = 0.0
        weight_total = 0.0

        for dist_km, temp in neighbours:
            # Guard against a station sitting exactly on top of another
            # (shouldn't happen with real-world coordinates, but be safe)
            effective_dist = max(dist_km, 0.1)
            weight = 1.0 / (effective_dist ** IDW_POWER)
            weighted_sum += weight * temp
            weight_total += weight

        predicted = weighted_sum / weight_total
        logger.debug(
            f"[Predict-IDW] station={station_id} | "
            f"{len(neighbours)} neighbour(s) within {SPATIAL_RADIUS_KM} km | "
            f"IDW T_predicted={predicted:.2f}°C"
        )
        return round(predicted, 2), len(neighbours)

    # ── Step 6: No nearby neighbours – fall back to own rolling mean ──
    logger.info(
        f"[Predict-IDW] station={station_id} | No neighbours within "
        f"{SPATIAL_RADIUS_KM} km. Falling back to own rolling mean."
    )
    own_avg = await _station_recent_avg(station_id, db, window)

    if own_avg is not None:
        logger.debug(
            f"[Predict-IDW] station={station_id} | "
            f"Own rolling mean T_predicted={own_avg:.2f}°C"
        )
        return round(own_avg, 2), 0

    # ── Step 7: Cold-start – no data at all ───────────────────────────
    logger.warning(
        f"[Predict-IDW] station={station_id} | No historical data and no "
        f"neighbours. Returning cold-start default {COLD_START_DEFAULT}°C."
    )
    return COLD_START_DEFAULT, 0


# ── Station statistics (unchanged, kept for the /stats endpoint) ──────

async def get_station_stats(
    station_id: str,
    db: AsyncSession,
) -> dict:
    """
    Return summary statistics for a station's historical readings.

    Returns:
        Dict with keys: station_id, reading_count, mean_temperature,
        min_temperature, max_temperature.
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
