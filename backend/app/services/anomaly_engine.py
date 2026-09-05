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

Confidence & Severity Scoring
──────────────────────────────
Each decision produces a confidence score (0–100) and a severity level
(LOW / MEDIUM / HIGH / CRITICAL) based on the magnitude and alignment
of the three pairwise temperature deltas.

Confidence quantifies *how clearly the evidence supports the decision*.
  • HIGH confidence → the delta pattern cleanly matches one case.
  • LOW  confidence → the pattern is ambiguous or borderline.

Severity quantifies *operational impact and urgency of response*.
  • Driven primarily by the magnitude of the key divergence delta.
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


# ═════════════════════════════════════════════════════════════════════════
# Confidence Scoring
# ═════════════════════════════════════════════════════════════════════════

def compute_confidence(
    decision: AnomalyDecision,
    diff_aws_witness: float,
    diff_aws_pred: float,
    diff_witness_pred: float,
    epsilon: float,
    delta: float,
) -> float:
    """
    Calculate a confidence score (0–100) indicating how clearly the
    three temperature deltas support the given arbitration decision.

    The score is composed of two components:
      • **Divergence strength** – How far above the threshold ε the
        primary divergence is.  Normalised against 5×ε as a practical
        ceiling (a reading 5× the anomaly threshold is unambiguous).
      • **Agreement strength** – How close the two "agreeing" sources
        are relative to δ.  Perfect agreement (delta=0) gives full
        marks; agreement exactly at δ gives zero.

    Formula per decision:
    ┌──────────────────┬────────────────────────────┬─────────────────────────────┐
    │ Decision         │ Divergence signal           │ Agreement signal             │
    ├──────────────────┼────────────────────────────┼─────────────────────────────┤
    │ PRIMARY_DRIFT    │ |AWS−W| / ε  (capped 5×)   │ 1 − |W−P| / δ               │
    │ WITNESS_FAULT    │ |AWS−W| / ε  (capped 5×)   │ 1 − |AWS−P| / δ             │
    │ TRUE_EXTREME     │ max(|AWS−P|,|W−P|) / ε     │ 1 − |AWS−W| / δ             │
    │ NORMAL           │ n/a                         │ 1 − max(Δ) / max(ε, δ)      │
    └──────────────────┴────────────────────────────┴─────────────────────────────┘

    Returns:
        Confidence score in [0.0, 100.0], rounded to 1 decimal.
    """
    if decision == AnomalyDecision.NORMAL:
        # ── NORMAL: confidence is higher when ALL deltas are small ────
        max_delta = max(diff_aws_witness, diff_aws_pred, diff_witness_pred)
        max_threshold = max(epsilon, delta)
        # Ranges from 85 (when max_delta ≈ threshold) to 100 (perfect)
        score = 85.0 + 15.0 * max(0.0, 1.0 - max_delta / max_threshold)
        return round(min(100.0, max(0.0, score)), 1)

    if decision == AnomalyDecision.PRIMARY_DRIFT:
        # ── PRIMARY_DRIFT: AWS diverged; Witness & Prediction agree ──
        divergence = min(diff_aws_witness / epsilon, 5.0) / 5.0   # 0→1
        agreement = max(0.0, 1.0 - diff_witness_pred / delta)      # 0→1
        score = 40.0 + divergence * 35.0 + agreement * 25.0
        return round(min(100.0, max(0.0, score)), 1)

    if decision == AnomalyDecision.WITNESS_FAULT:
        # ── WITNESS_FAULT: Witness diverged; AWS & Prediction agree ──
        divergence = min(diff_aws_witness / epsilon, 5.0) / 5.0
        agreement = max(0.0, 1.0 - diff_aws_pred / delta)
        score = 40.0 + divergence * 35.0 + agreement * 25.0
        return round(min(100.0, max(0.0, score)), 1)

    if decision == AnomalyDecision.TRUE_EXTREME:
        # ── TRUE_EXTREME: Both sensors agree but deviate from pred ───
        pred_deviation = max(diff_aws_pred, diff_witness_pred)
        divergence = min(pred_deviation / epsilon, 5.0) / 5.0
        agreement = max(0.0, 1.0 - diff_aws_witness / delta)
        score = 40.0 + divergence * 35.0 + agreement * 25.0
        return round(min(100.0, max(0.0, score)), 1)

    # Fallback (should never be reached)
    return 50.0


# ═════════════════════════════════════════════════════════════════════════
# Severity Grading
# ═════════════════════════════════════════════════════════════════════════

def compute_severity(
    decision: AnomalyDecision,
    diff_aws_witness: float,
    diff_aws_pred: float,
    diff_witness_pred: float,
) -> Severity:
    """
    Derive a severity level from the arbitration decision and the
    magnitude of the observed deltas.

    Graduated thresholds per decision type:

    ┌──────────────────┬────────────────────────────────────────────────┐
    │ Decision         │ Severity rule                                  │
    ├──────────────────┼────────────────────────────────────────────────┤
    │ NORMAL           │ Always LOW                                     │
    ├──────────────────┼────────────────────────────────────────────────┤
    │ PRIMARY_DRIFT    │ |AWS−W| > 8 → CRITICAL                        │
    │                  │ |AWS−W| > 5 → HIGH                             │
    │                  │ |AWS−W| > 3 → MEDIUM                           │
    │                  │ else        → LOW                              │
    ├──────────────────┼────────────────────────────────────────────────┤
    │ WITNESS_FAULT    │ |AWS−W| > 8 → HIGH  (witness issues are less  │
    │                  │ |AWS−W| > 4 → MEDIUM  operationally impactful) │
    │                  │ else        → LOW                              │
    ├──────────────────┼────────────────────────────────────────────────┤
    │ TRUE_EXTREME     │ max(|AWS−P|, |W−P|) > 8 → CRITICAL            │
    │                  │ max(|AWS−P|, |W−P|) > 5 → HIGH                 │
    │                  │ else                     → MEDIUM (always ≥ M) │
    └──────────────────┴────────────────────────────────────────────────┘

    Returns:
        One of Severity.LOW / MEDIUM / HIGH / CRITICAL.
    """
    if decision == AnomalyDecision.NORMAL:
        return Severity.LOW

    if decision == AnomalyDecision.PRIMARY_DRIFT:
        if diff_aws_witness > 8.0:
            return Severity.CRITICAL
        if diff_aws_witness > 5.0:
            return Severity.HIGH
        if diff_aws_witness > 3.0:
            return Severity.MEDIUM
        return Severity.LOW

    if decision == AnomalyDecision.WITNESS_FAULT:
        # Witness faults are less operationally impactful because the
        # official AWS data is still valid.  Cap at HIGH.
        if diff_aws_witness > 8.0:
            return Severity.HIGH
        if diff_aws_witness > 4.0:
            return Severity.MEDIUM
        return Severity.LOW

    if decision == AnomalyDecision.TRUE_EXTREME:
        # A genuine extreme event always warrants at least MEDIUM.
        deviation = max(diff_aws_pred, diff_witness_pred)
        if deviation > 8.0:
            return Severity.CRITICAL
        if deviation > 5.0:
            return Severity.HIGH
        return Severity.MEDIUM

    # Fallback (should not be reached)
    return Severity.LOW


# ═════════════════════════════════════════════════════════════════════════
# Three-Way Arbitration (decision + reason)
# ═════════════════════════════════════════════════════════════════════════

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


# ═════════════════════════════════════════════════════════════════════════
# ═════════════════════════════════════════════════════════════════════════
# Temperature Imputation (for PRIMARY_DRIFT)
# ═════════════════════════════════════════════════════════════════════════

def compute_imputed_temperature(
    t_witness: float,
    t_predicted: float,
    weight_witness: float = 0.6,
    weight_pred: float = 0.4,
) -> float:
    """
    Calculate an imputed (corrected) temperature value when PRIMARY_DRIFT is detected.

    When the official AWS sensor drifts, both T_Witness and T_Predicted remain trustworthy.
    A weighted combination is used:
        T_imputed = (0.6 * T_Witness) + (0.4 * T_Predicted)

    Parameters:
        t_witness      – Witness node temperature reading (°C).
        t_predicted    – ML-predicted baseline temperature (°C).
        weight_witness – Weight assigned to witness reading (default: 0.6).
        weight_pred    – Weight assigned to prediction baseline (default: 0.4).

    Returns:
        Calculated imputed temperature (°C), rounded to 2 decimal places.
    """
    imputed = (weight_witness * t_witness) + (weight_pred * t_predicted)
    return round(imputed, 2)


# ═════════════════════════════════════════════════════════════════════════
# Full Arbitration Pipeline
# ═════════════════════════════════════════════════════════════════════════

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
      2. Compute confidence score.
      3. Compute severity level.
      4. Calculate imputed temperature if PRIMARY_DRIFT.
      5. Persist the anomaly event.
      6. Return a structured response.

    Parameters:
        station_id  – Which station this evaluation is for.
        t_aws       – AWS temperature reading (°C).
        t_witness   – Witness node temperature reading (°C).
        t_predicted – Predicted temperature baseline (°C).
        db          – Active async database session.
        epsilon     – Optional override for the epsilon threshold.
        delta       – Optional override for the delta threshold.

    Returns:
        ArbitrationResponse with all computed fields including
        confidence, severity, and imputation metadata.
    """
    eps: float = epsilon if epsilon is not None else settings.EPSILON
    dlt: float = delta if delta is not None else settings.DELTA

    # Step 1 – Decide
    decision, reason = three_way_arbitration(
        t_aws, t_witness, t_predicted, epsilon=eps, delta=dlt
    )

    # Step 2 – Compute deltas
    diff_aws_witness = abs(t_aws - t_witness)
    diff_witness_pred = abs(t_witness - t_predicted)
    diff_aws_pred = abs(t_aws - t_predicted)

    # Step 3 – Compute confidence (0–100)
    confidence = compute_confidence(
        decision, diff_aws_witness, diff_aws_pred, diff_witness_pred,
        epsilon=eps, delta=dlt,
    )

    # Step 4 – Compute severity
    severity = compute_severity(
        decision, diff_aws_witness, diff_aws_pred, diff_witness_pred
    )

    # Step 5 – Handle Temperature Imputation
    original_t_aws = t_aws
    if decision == AnomalyDecision.PRIMARY_DRIFT:
        is_imputed = True
        t_imputed = compute_imputed_temperature(t_witness, t_predicted)
    else:
        is_imputed = False
        t_imputed = None

    logger.info(
        f"[Arbitration] station={station_id} → {decision.value} "
        f"(confidence={confidence}%, severity={severity.value}, "
        f"is_imputed={is_imputed}, t_imputed={t_imputed})"
    )

    # Step 6 – Persist the anomaly event
    event = AnomalyEvent(
        station_id=station_id,
        t_aws=t_aws,
        t_witness=t_witness,
        t_predicted=t_predicted,
        decision=decision,
        reason=reason,
        severity=severity,
        confidence=confidence,
        is_imputed=is_imputed,
        t_imputed=t_imputed,
        original_t_aws=original_t_aws,
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

    # Step 7 – Build response
    return ArbitrationResponse(
        station_id=station_id,
        decision=decision,
        reason=reason,
        severity=severity,
        confidence=confidence,
        t_aws=t_aws,
        t_witness=t_witness,
        t_predicted=t_predicted,
        is_imputed=is_imputed,
        t_imputed=t_imputed,
        original_t_aws=original_t_aws,
        diff_aws_witness=diff_aws_witness,
        diff_witness_pred=diff_witness_pred,
        diff_aws_pred=diff_aws_pred,
        anomaly_event_id=event.id,
    )
