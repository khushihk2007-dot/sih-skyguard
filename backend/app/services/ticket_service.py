"""
The Witness Network – Ticket Service
======================================
Manages anomaly-event tickets: querying, filtering, acknowledging,
and resolving detected anomalies.

Tickets are backed by the `anomaly_events` table; this service
provides higher-level operations on top of the raw ORM.
"""

from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.anomaly import (
    AnomalyDecision,
    AnomalyEvent,
    AnomalyEventResponse,
    Severity,
)


async def list_tickets(
    db: AsyncSession,
    station_id: Optional[str] = None,
    decision: Optional[AnomalyDecision] = None,
    severity: Optional[Severity] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AnomalyEventResponse]:
    """
    Query anomaly tickets with optional filters.

    Parameters:
        db         – Async database session.
        station_id – Filter by specific station.
        decision   – Filter by arbitration decision type.
        severity   – Filter by severity level.
        limit      – Maximum results to return.
        offset     – Pagination offset.

    Returns:
        List of anomaly event responses.
    """
    stmt = select(AnomalyEvent).order_by(AnomalyEvent.detected_at.desc())

    # Apply optional filters
    filters = []
    if station_id:
        filters.append(AnomalyEvent.station_id == station_id)
    if decision:
        filters.append(AnomalyEvent.decision == decision)
    if severity:
        filters.append(AnomalyEvent.severity == severity)

    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    events = result.scalars().all()

    return [AnomalyEventResponse.model_validate(e) for e in events]


async def get_ticket_by_id(
    ticket_id: int,
    db: AsyncSession,
) -> Optional[AnomalyEventResponse]:
    """Retrieve a single ticket by its primary key."""
    stmt = select(AnomalyEvent).where(AnomalyEvent.id == ticket_id)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if event is None:
        return None

    return AnomalyEventResponse.model_validate(event)


async def get_ticket_summary(db: AsyncSession) -> dict:
    """
    Return aggregated ticket statistics grouped by decision type.

    Returns:
        Dict with total count and per-decision breakdowns.
    """
    # Total count
    total_stmt = select(func.count(AnomalyEvent.id))
    total_result = await db.execute(total_stmt)
    total: int = total_result.scalar() or 0

    # Count per decision type
    breakdown_stmt = (
        select(
            AnomalyEvent.decision,
            func.count(AnomalyEvent.id).label("count"),
        )
        .group_by(AnomalyEvent.decision)
    )
    breakdown_result = await db.execute(breakdown_stmt)
    by_decision = {
        row.decision: row.count for row in breakdown_result.fetchall()
    }

    # Count per severity
    severity_stmt = (
        select(
            AnomalyEvent.severity,
            func.count(AnomalyEvent.id).label("count"),
        )
        .group_by(AnomalyEvent.severity)
    )
    severity_result = await db.execute(severity_stmt)
    by_severity = {
        row.severity: row.count for row in severity_result.fetchall()
    }

    return {
        "total_tickets": total,
        "by_decision": by_decision,
        "by_severity": by_severity,
    }
