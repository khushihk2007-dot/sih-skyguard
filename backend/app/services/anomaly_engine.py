"""
The Witness Network – Anomaly Engine (Three-Way Arbitration)
=============================================================
Core business logic that compares T_AWS, T_Witness, and T_Predicted
to detect sensor drift, witness faults, genuine extreme weather, or
normal operation.

Arbitration Matrix:
┌──────────────────────┬──────────────────────┬───────────────────────┐
│ Condition            │ Decision             │ Meaning               │
├──────────────────────┼──────────────────────┼───────────────────────┤
│ |AWS−W| > ε          │ PRIMARY_DRIFT        │ AWS sensor drifted    │
│   AND |W−P| < δ      │                      │                       │
├──────────────────────┼──────────────────────┼───────────────────────┤
│ |AWS−W| > ε          │ WITNESS_FAULT        │ Witness node faulty   │
│   AND |AWS−P| < δ    │                      │                       │
├──────────────────────┼──────────────────────┼───────────────────────┤
│ |AWS−W| < δ          │ TRUE_EXTREME         │ Real microclimate     │
│   AND (|AWS−P|>ε     │                      │ event                 │
│    OR  |W−P|>ε)      │                      │                       │
├──────────────────────┼──────────────────────┼───────────────────────┤
│ Otherwise            │ NORMAL               │ All readings agree    │
└──────────────────────┴──────────────────────┴───────────────────────┘
"""

from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.anomaly import (
    AnomalyDecision,
    AnomalyEvent,
    ArbitrationResponse,
    Severity,
)


def compute_severity(
    decision: AnomalyDecision,
    diff_aws_witness: float,
    diff_aws_pred: float,
    diff_witness_pred: float,
) -> Severity:
    """
    Derive a severity level from the arbitration decision and the
    magnitude of the observed deltas.

    Heuristic:
        - NORMAL            → LOW
        - Small drift/fault → MEDIUM
        - Large drift/fault → HIGH
        - TRUE_EXTREME      → CRITICAL (always – needs human review)
    """
    max_diff: float = max(diff_aws_witness, diff_aws_pred, diff_witness_pred)

    if decision == AnomalyDecision.NORMAL:
        return Severity.LOW

    if decision == AnomalyDecision.TRUE_EXTREME:
        return Severity.CRITICAL

    # PRIMARY_DRIFT or WITNESS_FAULT – grade by magnitude
    if max_diff > 5.0:
        return Severity.HIGH
    return Severity.MEDIUM


def three_way_arbitration(
    t_aws: float,
    t_witness: float,
    t_predicted: float,
    epsilon: float = settings.EPSILON,
    delta: float = settings.DELTA,
) -> tuple[AnomalyDecision, str]:
    """
    Core Three-Way Arbitration Logic.

    Compares the three temperature values and returns a classification
    decision along with a human-readable reason string.

    Parameters:
        t_aws       – Temperature from the official AWS station (°C).
        t_witness   – Temperature from the ESP32+BME280 witness node (°C).
        t_predicted – ML-predicted baseline temperature (°C).
        epsilon     – Max acceptable AWS↔Witness divergence.
        delta       – Max acceptable divergence from prediction baseline.

    Returns:
        Tuple of (AnomalyDecision, reason_string).
    """
    diff_aws_witness: float = abs(t_aws - t_witness)
    diff_witness_pred: float = abs(t_witness - t_predicted)
    diff_aws_pred: float = abs(t_aws - t_predicted)

    logger.debug(
        f"Arbitration inputs: T_AWS={t_aws}, T_W={t_witness}, T_P={t_predicted} | "
        f"|AWS−W|={diff_aws_witness:.2f}, |W−P|={diff_witness_pred:.2f}, "
        f"|AWS−P|={diff_aws_pred:.2f} | ε={epsilon}, δ={delta}"
    )

    # ── Case 1: AWS has drifted (witness & prediction agree) ──────
    if diff_aws_witness > epsilon and diff_witness_pred < delta:
        return (
            AnomalyDecision.PRIMARY_DRIFT,
            f"Official AWS sensor has drifted or failed. "
            f"|AWS−Witness|={diff_aws_witness:.2f}°C exceeds ε={epsilon}°C, "
            f"while |Witness−Predicted|={diff_witness_pred:.2f}°C is within δ={delta}°C.",
        )

    # ── Case 2: Witness node is faulty (AWS & prediction agree) ───
    if diff_aws_witness > epsilon and diff_aws_pred < delta:
        return (
            AnomalyDecision.WITNESS_FAULT,
            f"Witness node is faulty. Official data is still valid. "
            f"|AWS−Witness|={diff_aws_witness:.2f}°C exceeds ε={epsilon}°C, "
            f"while |AWS−Predicted|={diff_aws_pred:.2f}°C is within δ={delta}°C.",
        )

    # ── Case 3: Genuine extreme event (both sensors agree with each
    #            other but diverge from the prediction baseline) ────
    if diff_aws_witness < delta and (
        diff_aws_pred > epsilon or diff_witness_pred > epsilon
    ):
        return (
            AnomalyDecision.TRUE_EXTREME,
            f"Genuine extreme microclimate detected. "
            f"Both sensors agree (|AWS−Witness|={diff_aws_witness:.2f}°C < δ={delta}°C) "
            f"but deviate from prediction (|AWS−P|={diff_aws_pred:.2f}°C, "
            f"|W−P|={diff_witness_pred:.2f}°C).",
        )

    # ── Case 4: Everything is consistent ──────────────────────────
    return (
        AnomalyDecision.NORMAL,
        f"All readings are consistent. "
        f"|AWS−Witness|={diff_aws_witness:.2f}°C, "
        f"|AWS−P|={diff_aws_pred:.2f}°C, |W−P|={diff_witness_pred:.2f}°C.",
    )


async def run_arbitration(
    station_id: str,
    t_aws: float,
    t_witness: float,
    t_predicted: float,
    db: AsyncSession,
    epsilon: Optional[float] = None,
    delta: Optional[float] = None,
) -> ArbitrationResponse:
    """
    Execute the full arbitration pipeline:
      1. Run three-way comparison.
      2. Compute severity.
      3. Persist the anomaly event.
      4. Return a structured response.

    Parameters:
        station_id  – Which station this evaluation is for.
        t_aws       – AWS temperature reading (°C).
        t_witness   – Witness node temperature reading (°C).
        t_predicted – Predicted temperature baseline (°C).
        db          – Active async database session.
        epsilon     – Optional override for the epsilon threshold.
        delta       – Optional override for the delta threshold.

    Returns:
        ArbitrationResponse with all computed fields.
    """
    eps: float = epsilon if epsilon is not None else settings.EPSILON
    dlt: float = delta if delta is not None else settings.DELTA

    # Step 1 – Decide
    decision, reason = three_way_arbitration(
        t_aws, t_witness, t_predicted, epsilon=eps, delta=dlt
    )

    # Step 2 – Compute deltas & severity
    diff_aws_witness = abs(t_aws - t_witness)
    diff_witness_pred = abs(t_witness - t_predicted)
    diff_aws_pred = abs(t_aws - t_predicted)

    severity = compute_severity(
        decision, diff_aws_witness, diff_aws_pred, diff_witness_pred
    )

    logger.info(
        f"[Arbitration] station={station_id} → {decision.value} "
        f"(severity={severity.value})"
    )

    # Step 3 – Persist the anomaly event
    event = AnomalyEvent(
        station_id=station_id,
        t_aws=t_aws,
        t_witness=t_witness,
        t_predicted=t_predicted,
        decision=decision,
        reason=reason,
        severity=severity,
        diff_aws_witness=diff_aws_witness,
        diff_witness_pred=diff_witness_pred,
        diff_aws_pred=diff_aws_pred,
        epsilon_used=eps,
        delta_used=dlt,
        detected_at=datetime.utcnow(),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    # Step 4 – Build response
    return ArbitrationResponse(
        station_id=station_id,
        decision=decision,
        reason=reason,
        severity=severity,
        t_aws=t_aws,
        t_witness=t_witness,
        t_predicted=t_predicted,
        diff_aws_witness=diff_aws_witness,
        diff_witness_pred=diff_witness_pred,
        diff_aws_pred=diff_aws_pred,
        anomaly_event_id=event.id,
    )
