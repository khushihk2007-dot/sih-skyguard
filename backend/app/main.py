"""
The Witness Network – FastAPI Application Entry Point
======================================================
Smart Weather Anomaly & Tamper Detection System

This is the main FastAPI application that wires together:
  • Database lifecycle (init on startup, cleanup on shutdown)
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

from app.config import settings
from app.core.database import init_db
from app.core.mqtt_client import mqtt_client
from app.api.ingestion import router as ingestion_router
from app.api.stations import router as stations_router
from app.api.tickets import router as tickets_router


# ── Application Lifespan ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages startup and shutdown events for the application.

    Startup:
        1. Initialise the SQLite database (create tables).
        2. Start the MQTT listener for witness-node data.

    Shutdown:
        1. Stop the MQTT listener gracefully.
    """
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # ── Startup ───────────────────────────────────────────────────
    await init_db()
    logger.info("✅ Database initialised (tables created if needed)")

    await mqtt_client.start()
    logger.info("✅ MQTT client started")

    yield  # Application is running

    # ── Shutdown ──────────────────────────────────────────────────
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
