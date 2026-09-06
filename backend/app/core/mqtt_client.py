"""
The Witness Network – MQTT Client
===================================
Async MQTT subscriber that listens for real-time temperature
readings published by ESP32 + BME280 Witness Nodes.

Topic convention:  witness/<station_id>/temperature
Payload (JSON):    { "temperature": 32.5, "humidity": 65.2, "timestamp": "..." }
"""

import asyncio
import json
from typing import Optional, Callable, Awaitable

from loguru import logger

from app.config import settings

# aiomqtt is optional – the app can still run without a broker
try:
    import aiomqtt
    MQTT_AVAILABLE = True
except ImportError:
    aiomqtt = None  # type: ignore
    MQTT_AVAILABLE = False


# Type alias for the callback that processes incoming witness data
WitnessCallback = Callable[[str, float, Optional[float], str], Awaitable[None]]


class MQTTClient:
    """
    Manages the MQTT connection lifecycle and dispatches incoming
    witness-node messages to a registered callback.
    """

    def __init__(self) -> None:
        self._callback: Optional[WitnessCallback] = None
        self._task: Optional[asyncio.Task] = None

    def register_callback(self, callback: WitnessCallback) -> None:
        """Register the async function to call when a message arrives."""
        self._callback = callback

    async def start(self) -> None:
        """Begin listening in a background task if MQTT is enabled and available."""
        if not getattr(settings, "MQTT_ENABLED", False):
            logger.info("MQTT disabled in config – skipping client startup")
            return

        if not MQTT_AVAILABLE:
            logger.warning("aiomqtt not installed – MQTT listener disabled")
            return

        if self._task and not self._task.done():
            return

        self._task = asyncio.create_task(self._listen())
        logger.info(
            f"MQTT listener started on {settings.MQTT_BROKER_HOST}:"
            f"{settings.MQTT_BROKER_PORT}"
        )

    async def stop(self) -> None:
        """Cancel the background listener task."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("MQTT listener stopped")

    async def _listen(self) -> None:
        """
        Internal loop – connects to the broker, subscribes to the
        witness topic, and dispatches messages indefinitely.
        Automatically reconnects on failure without repeated error spam.
        """
        has_logged_error = False

        while True:
            try:
                async with aiomqtt.Client(
                    hostname=settings.MQTT_BROKER_HOST,
                    port=settings.MQTT_BROKER_PORT,
                    username=settings.MQTT_USERNAME,
                    password=settings.MQTT_PASSWORD,
                ) as client:
                    await client.subscribe(settings.MQTT_TOPIC_WITNESS)
                    logger.info(
                        f"Subscribed to topic: {settings.MQTT_TOPIC_WITNESS}"
                    )
                    has_logged_error = False

                    async for message in client.messages:
                        await self._handle_message(message)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                if not has_logged_error:
                    logger.warning(
                        f"MQTT connection error: {exc}. Retrying in background..."
                    )
                    has_logged_error = True
                else:
                    logger.debug(f"MQTT reconnect failed: {exc}")
                await asyncio.sleep(5)

    async def _handle_message(self, message) -> None:
        """Parse an incoming MQTT message and invoke the registered callback."""
        try:
            topic_parts = str(message.topic).split("/")
            # Expected: witness/<station_id>/temperature
            station_id = topic_parts[1] if len(topic_parts) >= 3 else "unknown"

            payload: dict = json.loads(message.payload.decode())
            temperature: float = float(payload["temperature"])
            humidity: Optional[float] = payload.get("humidity")
            timestamp: str = payload.get("timestamp", "")

            logger.debug(
                f"[MQTT] station={station_id}  T={temperature}°C  H={humidity}%"
            )

            if self._callback:
                await self._callback(station_id, temperature, humidity, timestamp)

        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning(f"Malformed MQTT payload: {exc}")


# Singleton instance
mqtt_client = MQTTClient()
