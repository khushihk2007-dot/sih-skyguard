"""
The Witness Network – Thermodynamic Consistency Gate (Layer 1)
===============================================================
WMO-inspired sanity check that validates weather readings against
fundamental thermodynamic relationships BEFORE the Three-Way
Arbitration (Layer 2) ever runs.

Purpose:
    Catch physically impossible or implausible readings early.
    A sensor that reports 45 °C with 100 % relative humidity is
    thermodynamically absurd — the atmosphere simply cannot hold
    that much moisture at that temperature under normal surface
    pressures.  This layer rejects or flags such readings so the
    downstream arbitration engine only operates on plausible data.

Theory:
    ┌──────────────────────────────────────────────────────────┐
    │  August-Roche-Magnus Approximation (WMO recommended)    │
    │                                                          │
    │  Saturation vapor pressure:                              │
    │     e_s(T) = 6.112 × exp(17.67 × T / (T + 243.5))      │
    │                                                          │
    │  Actual vapor pressure:                                  │
    │     e = (RH / 100) × e_s(T)                              │
    │                                                          │
    │  Vapor Pressure Deficit:                                 │
    │     VPD = e_s(T) - e                                     │
    │                                                          │
    │  Dew-point temperature:                                  │
    │     T_d = (243.5 × ln(e / 6.112))                        │
    │         / (17.67 - ln(e / 6.112))                        │
    └──────────────────────────────────────────────────────────┘

Checks performed:
    1. Temperature within terrestrial bounds  [-89.2 °C, 56.7 °C].
    2. Relative Humidity within [0 %, 100 %].
    3. VPD plausibility – extremely low VPD (< 0.05 hPa) at high
       temperatures (> 40 °C) is physically suspect.
    4. Atmospheric pressure within realistic surface bounds
       [870 hPa, 1083.8 hPa] (WMO extremes).
    5. Cross-parameter consistency: if pressure is supplied, verify
       that vapor pressure does not exceed total atmospheric pressure.
"""

import math
from enum import Enum
from typing import Optional

from loguru import logger
from pydantic import BaseModel, Field


# ═════════════════════════════════════════════════════════════════════════
# Constants
# ═════════════════════════════════════════════════════════════════════════

# August-Roche-Magnus coefficients (WMO recommended)
MAGNUS_A: float = 17.67
MAGNUS_B: float = 243.5   # °C
MAGNUS_C: float = 6.112   # hPa (reference saturation pressure at 0 °C)

# WMO-recorded terrestrial extremes
TEMP_MIN_TERRESTRIAL: float = -89.2   # °C  (Vostok Station, Antarctica)
TEMP_MAX_TERRESTRIAL: float = 56.7    # °C  (Death Valley, USA)

# Surface pressure extremes (WMO)
PRESSURE_MIN: float = 870.0     # hPa  (Typhoon Tip, 1979)
PRESSURE_MAX: float = 1083.8    # hPa  (Agata, Siberia, 1968)

# VPD thresholds
VPD_SUSPECT_THRESHOLD: float = 0.05   # hPa – suspiciously low VPD
VPD_HIGH_TEMP_GATE: float = 40.0      # °C  – high-temp regime

# Super-saturation tolerance (slight overshoot allowed for sensor noise)
SUPERSATURATION_TOLERANCE: float = 1.02  # 2 % above e_s is tolerated


# ═════════════════════════════════════════════════════════════════════════
# Consistency verdict
# ═════════════════════════════════════════════════════════════════════════

class ConsistencyVerdict(str, Enum):
    """Outcome of the thermodynamic consistency gate."""
    PASS = "PASS"             # All checks passed – proceed to arbitration
    SUSPECT = "SUSPECT"       # Marginal – proceed with caution flag
    FAIL = "FAIL"             # Physically implausible – reject / quarantine


class ThermodynamicFlag(BaseModel):
    """A single failed or warned consistency check."""
    check: str = Field(..., description="Short identifier of the check")
    message: str = Field(..., description="Human-readable explanation")
    severity: ConsistencyVerdict = Field(
        ..., description="FAIL or SUSPECT"
    )


class ThermodynamicResult(BaseModel):
    """Full result of the thermodynamic consistency gate."""
    verdict: ConsistencyVerdict
    temperature: float
    humidity: float
    pressure: Optional[float] = None

    # Computed thermodynamic quantities
    saturation_vapor_pressure: float = Field(
        ..., description="e_s(T) in hPa"
    )
    actual_vapor_pressure: float = Field(
        ..., description="e in hPa"
    )
    vapor_pressure_deficit: float = Field(
        ..., description="VPD = e_s - e in hPa"
    )
    dewpoint: Optional[float] = Field(
        None, description="Dew-point temperature in °C"
    )

    flags: list[ThermodynamicFlag] = Field(
        default_factory=list,
        description="List of individual check results (empty = all passed)",
    )


# ═════════════════════════════════════════════════════════════════════════
# Core thermodynamic functions
# ═════════════════════════════════════════════════════════════════════════

def saturation_vapor_pressure(temperature: float) -> float:
    """
    Calculate the saturation vapor pressure e_s(T) using the
    August-Roche-Magnus approximation.

        e_s(T) = 6.112 × exp(17.67 × T / (T + 243.5))

    Parameters:
        temperature – Air temperature in °C.

    Returns:
        Saturation vapor pressure in hPa (millibars).
    """
    return MAGNUS_C * math.exp(
        (MAGNUS_A * temperature) / (temperature + MAGNUS_B)
    )


def actual_vapor_pressure(
    temperature: float,
    humidity: float,
) -> float:
    """
    Calculate the actual vapor pressure from temperature and RH.

        e = (RH / 100) × e_s(T)

    Parameters:
        temperature – Air temperature in °C.
        humidity    – Relative humidity in %.

    Returns:
        Actual vapor pressure in hPa.
    """
    e_s = saturation_vapor_pressure(temperature)
    return (humidity / 100.0) * e_s


def vapor_pressure_deficit(
    temperature: float,
    humidity: float,
) -> float:
    """
    Calculate the Vapor Pressure Deficit.

        VPD = e_s(T) - e

    A large VPD means the air is dry; a near-zero VPD means the air
    is close to saturation (fog/dew conditions).

    Parameters:
        temperature – Air temperature in °C.
        humidity    – Relative humidity in %.

    Returns:
        VPD in hPa.
    """
    e_s = saturation_vapor_pressure(temperature)
    e = actual_vapor_pressure(temperature, humidity)
    return e_s - e


def dewpoint_temperature(
    temperature: float,
    humidity: float,
) -> Optional[float]:
    """
    Estimate the dew-point temperature using the inverse Magnus formula.

        T_d = (243.5 × ln(e / 6.112)) / (17.67 - ln(e / 6.112))

    Returns None if the actual vapor pressure is ≤ 0 (would produce
    an undefined logarithm — possible with RH = 0 %).

    Parameters:
        temperature – Air temperature in °C.
        humidity    – Relative humidity in %.

    Returns:
        Dew-point temperature in °C, or None.
    """
    e = actual_vapor_pressure(temperature, humidity)
    if e <= 0:
        return None

    ln_ratio = math.log(e / MAGNUS_C)
    denominator = MAGNUS_A - ln_ratio
    if denominator == 0:
        return None

    return round((MAGNUS_B * ln_ratio) / denominator, 2)


# ═════════════════════════════════════════════════════════════════════════
# Main consistency check
# ═════════════════════════════════════════════════════════════════════════

async def check_thermodynamic_consistency(
    temperature: float,
    humidity: float,
    pressure: float | None = None,
) -> dict:
    """
    Layer 1 — Thermodynamic Consistency Gate.

    Validates that the supplied weather readings are physically
    plausible before they enter the Three-Way Arbitration pipeline.

    Parameters:
        temperature – Air temperature in °C.
        humidity    – Relative humidity in %.
        pressure    – Atmospheric pressure in hPa (optional).

    Returns:
        Dict representation of ThermodynamicResult with:
            verdict                    – PASS / SUSPECT / FAIL
            saturation_vapor_pressure  – e_s(T) in hPa
            actual_vapor_pressure      – e in hPa
            vapor_pressure_deficit     – VPD in hPa
            dewpoint                   – T_d in °C (or None)
            flags                      – list of flagged checks
    """
    flags: list[ThermodynamicFlag] = []

    # ── Check 1: Temperature within terrestrial bounds ────────────────
    if temperature < TEMP_MIN_TERRESTRIAL or temperature > TEMP_MAX_TERRESTRIAL:
        flags.append(ThermodynamicFlag(
            check="TEMP_BOUNDS",
            message=(
                f"Temperature {temperature}°C is outside terrestrial records "
                f"[{TEMP_MIN_TERRESTRIAL}°C, {TEMP_MAX_TERRESTRIAL}°C]."
            ),
            severity=ConsistencyVerdict.FAIL,
        ))

    # ── Check 2: Relative Humidity within [0, 100] ────────────────────
    if humidity < 0.0 or humidity > 100.0:
        flags.append(ThermodynamicFlag(
            check="RH_BOUNDS",
            message=(
                f"Relative humidity {humidity}% is outside valid range "
                f"[0%, 100%]."
            ),
            severity=ConsistencyVerdict.FAIL,
        ))

    # ── Compute thermodynamic quantities ──────────────────────────────
    # Clamp inputs to safe ranges for math (avoids domain errors in
    # downstream formulas even when the checks above flag them).
    safe_temp = max(min(temperature, 60.0), -90.0)
    safe_rh = max(min(humidity, 100.0), 0.0)

    e_s = saturation_vapor_pressure(safe_temp)
    e = actual_vapor_pressure(safe_temp, safe_rh)
    vpd = e_s - e
    t_dew = dewpoint_temperature(safe_temp, safe_rh)

    # ── Check 3: Supersaturation guard ────────────────────────────────
    #   Actual vapor pressure should not exceed saturation by more than
    #   the sensor-noise tolerance.
    if e > e_s * SUPERSATURATION_TOLERANCE:
        flags.append(ThermodynamicFlag(
            check="SUPERSATURATION",
            message=(
                f"Actual vapor pressure ({e:.2f} hPa) exceeds saturation "
                f"({e_s:.2f} hPa) by more than {(SUPERSATURATION_TOLERANCE - 1) * 100:.0f}% — "
                f"supersaturation is physically implausible at surface level."
            ),
            severity=ConsistencyVerdict.FAIL,
        ))

    # ── Check 4: VPD plausibility at high temperatures ────────────────
    #   Near-zero VPD at very high temperatures is suspicious:
    #   e.g., 50 °C and 100 % RH almost never occurs in nature.
    if safe_temp > VPD_HIGH_TEMP_GATE and vpd < VPD_SUSPECT_THRESHOLD:
        flags.append(ThermodynamicFlag(
            check="VPD_HIGH_TEMP",
            message=(
                f"VPD is suspiciously low ({vpd:.3f} hPa) at high "
                f"temperature ({temperature}°C). Near-saturation at "
                f">{VPD_HIGH_TEMP_GATE}°C is extremely rare in surface "
                f"observations."
            ),
            severity=ConsistencyVerdict.SUSPECT,
        ))

    # ── Check 5: Atmospheric pressure bounds (if supplied) ────────────
    if pressure is not None:
        if pressure < PRESSURE_MIN or pressure > PRESSURE_MAX:
            flags.append(ThermodynamicFlag(
                check="PRESSURE_BOUNDS",
                message=(
                    f"Atmospheric pressure {pressure} hPa is outside WMO "
                    f"recorded extremes [{PRESSURE_MIN}, {PRESSURE_MAX}] hPa."
                ),
                severity=ConsistencyVerdict.FAIL,
            ))

        # ── Check 6: Vapor pressure vs total atmospheric pressure ─────
        #   Vapor pressure can never exceed total atmospheric pressure.
        if e > pressure:
            flags.append(ThermodynamicFlag(
                check="VAPOR_GT_PRESSURE",
                message=(
                    f"Actual vapor pressure ({e:.2f} hPa) exceeds total "
                    f"atmospheric pressure ({pressure} hPa) — physically "
                    f"impossible."
                ),
                severity=ConsistencyVerdict.FAIL,
            ))

    # ── Determine overall verdict ─────────────────────────────────────
    if any(f.severity == ConsistencyVerdict.FAIL for f in flags):
        verdict = ConsistencyVerdict.FAIL
    elif any(f.severity == ConsistencyVerdict.SUSPECT for f in flags):
        verdict = ConsistencyVerdict.SUSPECT
    else:
        verdict = ConsistencyVerdict.PASS

    # ── Build result ──────────────────────────────────────────────────
    result = ThermodynamicResult(
        verdict=verdict,
        temperature=temperature,
        humidity=humidity,
        pressure=pressure,
        saturation_vapor_pressure=round(e_s, 4),
        actual_vapor_pressure=round(e, 4),
        vapor_pressure_deficit=round(vpd, 4),
        dewpoint=t_dew,
        flags=flags,
    )

    logger.info(
        f"[Thermodynamic] T={temperature}°C  RH={humidity}%  "
        f"P={pressure} hPa → verdict={verdict.value}  "
        f"e_s={e_s:.2f}  e={e:.2f}  VPD={vpd:.2f}  "
        f"T_dew={t_dew}°C  flags={len(flags)}"
    )

    return result.model_dump()
