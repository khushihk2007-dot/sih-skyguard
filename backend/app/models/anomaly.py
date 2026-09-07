"""
The Witness Network – Anomaly Models
======================================
SQLAlchemy ORM model and Pydantic schemas for anomaly events
produced by the Three-Way Arbitration Engine.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    Enum as SAEnum,
)
from app.core.database import Base


# ── Anomaly Decision Enum ─────────────────────────────────────────────

class AnomalyDecision(str, Enum):
    """
    Possible outcomes of the Three-Way Arbitration Logic.

    PRIMARY_DRIFT  – Official AWS sensor has drifted or failed.
    WITNESS_FAULT  – The witness node is reporting bad data.
    TRUE_EXTREME   – Genuine localised microclimate event.
    NORMAL         – All three readings are consistent.
    """
    PRIMARY_DRIFT = "PRIMARY_DRIFT"
    WITNESS_FAULT = "WITNESS_FAULT"
    TRUE_EXTREME = "TRUE_EXTREME"
    NORMAL = "NORMAL"


# ── Severity Levels ──────────────────────────────────────────────────

class Severity(str, Enum):
    """Severity classification for anomaly tickets."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ── SQLAlchemy ORM Model ─────────────────────────────────────────────

class AnomalyEvent(Base):
    """
    Persistent record of an anomaly detected by the arbitration engine.

    Each row links back to the sensor readings that triggered the
    anomaly and captures the engine's decision + confidence metadata.
    """

    __tablename__ = "anomaly_events"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    station_id: str = Column(String(64), nullable=False, index=True)

    # The three temperatures that were compared
    t_aws: float = Column(Float, nullable=False)
    t_witness: float = Column(Float, nullable=False)
    t_predicted: float = Column(Float, nullable=False)

    # Arbitration result
    decision: str = Column(SAEnum(AnomalyDecision), nullable=False, index=True)
    reason: str = Column(Text, nullable=False)
    severity: str = Column(SAEnum(Severity), nullable=False, default=Severity.LOW)
    confidence: float = Column(Float, nullable=False, default=0.0)

    # Imputation fields
    is_imputed: bool = Column(Boolean, nullable=False, default=False)
    t_imputed: Optional[float] = Column(Float, nullable=True)
    original_t_aws: float = Column(Float, nullable=False)

    # Spatial context
    neighbours_used: Optional[int] = Column(Integer, nullable=True, default=0)

    # Deltas recorded at decision time
    diff_aws_witness: float = Column(Float, nullable=False)
    diff_witness_pred: float = Column(Float, nullable=False)
    diff_aws_pred: float = Column(Float, nullable=False)

    # Thresholds that were active when the decision was made
    epsilon_used: float = Column(Float, nullable=False)
    delta_used: float = Column(Float, nullable=False)

    # Advanced analytics – Mahalanobis-style anomaly score
    # Quantifies the statistical distance of the residual vector from
    # the expected-normal distribution.  Computed alongside confidence.
    #   ≈ 0.0 – 1.5  → consistent / normal
    #   ≈ 1.5 – 3.0  → mild anomaly
    #   ≥ 3.0        → strong anomaly
    # Nullable for rows created before this field was introduced.
    mahalanobis_score: Optional[float] = Column(Float, nullable=True, default=0.0)

    # Timestamps
    detected_at: datetime = Column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return (
            f"<AnomalyEvent station={self.station_id} "
            f"decision={self.decision} @ {self.detected_at}>"
        )


# ── Pydantic Schemas ─────────────────────────────────────────────────

class AnomalyEventResponse(BaseModel):
    """Schema returned when querying anomaly events."""

    id: int
    station_id: str
    t_aws: float
    t_witness: float
    t_predicted: float
    neighbours_used: Optional[int] = None
    decision: AnomalyDecision
    reason: str
    severity: Severity
    confidence: float
    is_imputed: bool = False
    t_imputed: Optional[float] = None
    original_t_aws: Optional[float] = None
    diff_aws_witness: float
    diff_witness_pred: float
    diff_aws_pred: float
    epsilon_used: float
    delta_used: float
    mahalanobis_score: float = 0.0
    detected_at: datetime

    class Config:
        from_attributes = True


class ArbitrationRequest(BaseModel):
    """Manual arbitration request for testing or ad-hoc analysis."""

    station_id: str = Field(..., description="Station to evaluate")
    t_aws: float = Field(..., description="Official AWS temperature (°C)")
    t_witness: float = Field(..., description="Witness node temperature (°C)")
    t_predicted: Optional[float] = Field(
        None,
        description="ML-predicted temperature (°C). If omitted, the "
                    "prediction service will generate one.",
    )
    epsilon: Optional[float] = Field(
        None, description="Override default epsilon threshold"
    )
    delta: Optional[float] = Field(
        None, description="Override default delta threshold"
    )


class ArbitrationResponse(BaseModel):
    """Result of a Three-Way Arbitration evaluation."""

    station_id: str
    decision: AnomalyDecision
    reason: str
    severity: Severity
    confidence: float
    t_aws: float
    t_witness: float
    t_predicted: float
    neighbours_used: Optional[int] = None
    is_imputed: bool = False
    t_imputed: Optional[float] = None
    original_t_aws: Optional[float] = None
    diff_aws_witness: float
    diff_witness_pred: float
    diff_aws_pred: float
    anomaly_event_id: Optional[int] = None
    mahalanobis_score: float = 0.0
    mahalanobis_label: str = "consistent"
