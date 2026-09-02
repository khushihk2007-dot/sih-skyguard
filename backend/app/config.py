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

    # ── Prediction Service ────────────────────────────────────────────
    # Number of historical readings used for rolling-window prediction
    PREDICTION_WINDOW_SIZE: int = 24

    # ── CORS Origins (comma-separated in env) ─────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton settings instance – import this everywhere
settings = Settings()
