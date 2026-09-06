"""
The Witness Network – FastAPI Application Entry Point
======================================================
Smart Weather Anomaly & Tamper Detection System

This is the main FastAPI application that wires together:
  • Database lifecycle (init on startup, cleanup on shutdown)
  • Station registry seeding (12 IMD/AWS demo stations)
  • MQTT listener for real-time Witness Node data
  • REST API routers for ingestion, stations, and tickets
  • CORS middleware for frontend integration
  • Health-check endpoint

Run with:
    uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from sqlalchemy import select

from app.config import settings
from app.core.database import init_db, async_session
from app.core.mqtt_client import mqtt_client
from app.api.ingestion import router as ingestion_router
from app.api.stations import router as stations_router
from app.api.tickets import router as tickets_router

# Import the models package so all ORM models register with Base.metadata
# BEFORE init_db() calls create_all(). This ensures the `stations` table
# (and any future models) are picked up automatically.
import app.models  # noqa: F401
from app.models.station import Station


# ── Seed Data: 12 Real IMD/AWS Stations ──────────────────────────────
# Station IDs match the frontend DEMO_STATIONS in api.ts
# (e.g. AWS-DEL-001, AWS-MUM-001, AWS-BLR-001, etc.)

SEED_STATIONS: list[dict] = [
    {"id": "AWS-DEL-001", "name": "New Delhi – Safdarjung",   "latitude": 28.58, "longitude": 77.21},
    {"id": "AWS-MUM-001", "name": "Mumbai – Colaba",          "latitude": 18.91, "longitude": 72.81},
    {"id": "AWS-BLR-001", "name": "Bengaluru – HAL Airport",  "latitude": 12.95, "longitude": 77.67},
    {"id": "AWS-CHN-001", "name": "Chennai – Nungambakkam",   "latitude": 13.06, "longitude": 80.25},
    {"id": "AWS-KOL-001", "name": "Kolkata – Dum Dum",        "latitude": 22.65, "longitude": 88.45},
    {"id": "AWS-HYD-001", "name": "Hyderabad – Begumpet",     "latitude": 17.44, "longitude": 78.47},
    {"id": "AWS-JAI-001", "name": "Jaipur – Sanganer",        "latitude": 26.82, "longitude": 75.81},
    {"id": "AWS-LKO-001", "name": "Lucknow – Amausi",         "latitude": 26.76, "longitude": 80.89},
    {"id": "AWS-PAT-001", "name": "Patna",                    "latitude": 25.61, "longitude": 85.14},
    {"id": "AWS-GUW-001", "name": "Guwahati – Borjhar",       "latitude": 26.10, "longitude": 91.59},
    {"id": "AWS-TRV-001", "name": "Thiruvananthapuram",       "latitude":  8.52, "longitude": 76.94},
    {"id": "AWS-PNQ-001", "name": "Pune – Lohegaon",          "latitude": 18.58, "longitude": 73.92},
]


async def seed_stations() -> None:
    """
    Seed the 12 demo IMD/AWS stations into the database.
    Idempotent – skips any station whose ID already exists.
    """
    async with async_session() as session:
        inserted = 0
        for data in SEED_STATIONS:
            # Check if this station already exists
            existing = await session.execute(
                select(Station).where(Station.id == data["id"])
            )
            if existing.scalar_one_or_none() is None:
                station = Station(
                    id=data["id"],
                    name=data["name"],
                    latitude=data["latitude"],
                    longitude=data["longitude"],
                )
                session.add(station)
                inserted += 1

        if inserted > 0:
            await session.commit()
            logger.info(f"🌱 Seeded {inserted} new station(s) into the registry")
        else:
            logger.info("🌱 All 12 stations already present – skipping seed")


# ── Lightweight Schema Migrations ────────────────────────────────────

async def run_migrations() -> None:
    """
    Check for missing columns and add them via ALTER TABLE.
    SQLAlchemy's create_all() only creates missing *tables*, not
    missing *columns* on existing tables.  This function is idempotent.
    """
    async with async_session() as session:
        # Fetch existing column names for anomaly_events
        result = await session.execute(
            __import__("sqlalchemy").text(
                "PRAGMA table_info(anomaly_events)"
            )
        )
        existing_cols = {row[1] for row in result.fetchall()}

        if "confidence" not in existing_cols:
            await session.execute(
                __import__("sqlalchemy").text(
                    "ALTER TABLE anomaly_events "
                    "ADD COLUMN confidence FLOAT NOT NULL DEFAULT 0.0"
                )
            )
            await session.commit()
            logger.info(
                "🔧 Migration: added 'confidence' column to anomaly_events"
            )

        if "is_imputed" not in existing_cols:
            await session.execute(
                __import__("sqlalchemy").text(
                    "ALTER TABLE anomaly_events "
                    "ADD COLUMN is_imputed BOOLEAN NOT NULL DEFAULT 0"
                )
            )
            await session.commit()
            logger.info(
                "🔧 Migration: added 'is_imputed' column to anomaly_events"
            )

        if "t_imputed" not in existing_cols:
            await session.execute(
                __import__("sqlalchemy").text(
                    "ALTER TABLE anomaly_events "
                    "ADD COLUMN t_imputed FLOAT NULL"
                )
            )
            await session.commit()
            logger.info(
                "🔧 Migration: added 't_imputed' column to anomaly_events"
            )

        if "original_t_aws" not in existing_cols:
            await session.execute(
                __import__("sqlalchemy").text(
                    "ALTER TABLE anomaly_events "
                    "ADD COLUMN original_t_aws FLOAT NULL"
                )
            )
            await session.commit()
            logger.info(
                "🔧 Migration: added 'original_t_aws' column to anomaly_events"
            )

        if "neighbours_used" not in existing_cols:
            await session.execute(
                __import__("sqlalchemy").text(
                    "ALTER TABLE anomaly_events "
                    "ADD COLUMN neighbours_used INTEGER NULL"
                )
            )
            await session.commit()
            logger.info(
                "🔧 Migration: added 'neighbours_used' column to anomaly_events"
            )


# ── Application Lifespan ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages startup and shutdown events for the application.

    Startup:
        1. Initialise the SQLite database (create tables).
        2. Run lightweight schema migrations.
        3. Seed the 12 IMD/AWS demo stations (idempotent).
        4. Start the MQTT listener for witness-node data.

    Shutdown:
        1. Stop the MQTT listener gracefully.
    """
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # ── Startup ───────────────────────────────────────────────────
    await init_db()
    logger.info("✅ Database initialised (tables created if needed)")

    await run_migrations()

    await seed_stations()

    if settings.MQTT_ENABLED:
        await mqtt_client.start()
        logger.info("✅ MQTT client started")
    else:
        logger.info("MQTT disabled – skipping client startup")

    yield  # Application is running

    # ── Shutdown ──────────────────────────────────────────────────
    if settings.MQTT_ENABLED:
        await mqtt_client.stop()
    logger.info("🛑 Application shut down cleanly")


# ── FastAPI App Instance ──────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Smart Weather Anomaly & Tamper Detection System.\n\n"
        "Compares official AWS temperature data (Stream A) against "
        "ESP32+BME280 Witness Node readings (Stream B) using a "
        "Three-Way Arbitration Engine backed by ML predictions."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── CORS Middleware ───────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Register API Routers ─────────────────────────────────────────────

app.include_router(ingestion_router)
app.include_router(stations_router)
app.include_router(tickets_router)


# ── Health Check ──────────────────────────────────────────────────────

@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    description="Returns the application status and current timestamp.",
)
async def health_check() -> dict:
    """Simple health-check endpoint for Docker / load-balancer probes."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get(
    "/",
    tags=["System"],
    summary="Root endpoint",
)
async def root() -> dict:
    """Welcome message with links to documentation."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }
