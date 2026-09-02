"""
The Witness Network – Utility Helpers
=======================================
General-purpose helper functions used across the application.
"""

from datetime import datetime, timezone
from typing import Any, Optional


def utc_now() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def iso_format(dt: Optional[datetime]) -> Optional[str]:
    """
    Convert a datetime to an ISO-8601 string, or return None.

    Parameters:
        dt – datetime object to format.

    Returns:
        ISO-8601 formatted string or None.
    """
    return dt.isoformat() if dt else None


def clamp(value: float, low: float, high: float) -> float:
    """
    Clamp a numeric value within [low, high].

    Parameters:
        value – The value to clamp.
        low   – Lower bound (inclusive).
        high  – Upper bound (inclusive).

    Returns:
        The clamped value.
    """
    return max(low, min(value, high))


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Perform division with a fallback for zero-denominator cases.

    Parameters:
        numerator   – The dividend.
        denominator – The divisor.
        default     – Value to return if denominator is zero.

    Returns:
        Result of division, or default.
    """
    if denominator == 0:
        return default
    return numerator / denominator


def format_temperature(temp: float, unit: str = "C") -> str:
    """
    Format a temperature value with unit suffix.

    Parameters:
        temp – Temperature value.
        unit – "C" for Celsius, "F" for Fahrenheit.

    Returns:
        Formatted string like "32.50°C".
    """
    return f"{temp:.2f}°{unit}"


def build_response(
    status: str,
    message: str,
    data: Optional[Any] = None,
) -> dict:
    """
    Build a standardised JSON response envelope.

    Parameters:
        status  – "success", "error", etc.
        message – Human-readable description.
        data    – Optional payload.

    Returns:
        Dict conforming to the response envelope pattern.
    """
    response: dict = {
        "status": status,
        "message": message,
        "timestamp": utc_now().isoformat(),
    }
    if data is not None:
        response["data"] = data
    return response
