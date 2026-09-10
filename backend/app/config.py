"""
The Witness Network – Application Configuration
=================================================
Central configuration using Pydantic Settings.
All tuneable thresholds (epsilon, delta) and environment
variables are defined here.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Global application settings loaded from environment or .env file."""

    # ── Application Metadata ──────────────────────────────────────────
    APP_NAME: str = "The Witness Network"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./witness_network.db"

    # ── MQTT Broker (for ESP32 Witness Nodes) ─────────────────────────
    MQTT_ENABLED: bool = False
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_TOPIC_WITNESS: str = "witness/+/temperature"
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None

    # ── Three-Way Arbitration Thresholds ──────────────────────────────
    # epsilon (ε): Maximum acceptable divergence between AWS and Witness
    #   readings before flagging a discrepancy.
    EPSILON: float = 2.0

    # delta (δ): Maximum acceptable divergence of any single reading
    #   from the ML-predicted baseline.
    DELTA: float = 1.5

    # ── Mahalanobis Score Variance Terms ──────────────────────────────
    # Diagonal covariance approximation for the residual vector
    #   r = [r1, r2, r3] = [T_AWS−T_W, T_AWS−T_P, T_W−T_P].
    #
    # Each v_i represents the expected variance (σ²) for that residual
    # under normal operating conditions.  A residual of √v_i is treated
    # as one standard deviation of "normal" spread.  Tune these to
    # match observed baseline noise in the deployed environment.
    #
    #   v1 = Var(T_AWS − T_Witness)   ← typical inter-sensor spread ~1.5°C → var≈2.25
    #   v2 = Var(T_AWS − T_Predicted) ← prediction model error ~1.0°C    → var≈1.00
    #   v3 = Var(T_Witness − T_Pred)  ← witness vs model spread  ~1.2°C  → var≈1.44
    MAHAL_VAR_AWS_WITNESS: float = 2.25
    MAHAL_VAR_AWS_PRED:    float = 1.00
    MAHAL_VAR_WITNESS_PRED: float = 1.44

    # ── Prediction Service ────────────────────────────────────────────
    # Number of historical readings used for rolling-window prediction
    PREDICTION_WINDOW_SIZE: int = 24

    # ── CORS Origins (comma-separated in env) ─────────────────────────
    CORS_ORIGINS: list[str] = [
        "https://sih-skyguard.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton settings instance – import this everywhere
settings = Settings()
