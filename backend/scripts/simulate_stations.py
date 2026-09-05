"""
The Witness Network – Station Data Simulator
==============================================
Standalone async script that feeds realistic mock temperature data
into the running FastAPI backend via POST /api/ingest/arbitrate.

It cycles through all 12 IMD/AWS stations every tick, generating
T_AWS, T_Witness, and T_Predicted values.  Most stations stay NORMAL,
but three hardcoded scenarios create a guaranteed demo story:

  Tick 1–3 : All 12 stations report NORMAL readings.
  Tick 4+  : Delhi   → PRIMARY_DRIFT  (AWS sensor drifts +6°C)
             Mumbai  → WITNESS_FAULT  (Witness node glitches +7°C)
  Tick 6+  : Chennai → TRUE_EXTREME   (both sensors jump +8°C, real heatwave)

Usage (run in a separate terminal while uvicorn is up):

    cd backend
    python scripts/simulate_stations.py              # default 8s interval
    python scripts/simulate_stations.py --interval 5 # custom interval
    python scripts/simulate_stations.py --reset      # placeholder reset flag

Requirements:
    httpx (already in requirements.txt)
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
from datetime import datetime
from typing import Optional

import httpx

# Force UTF-8 output on Windows (cp1252 can't render box-drawing chars)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

# Backend base URL (change if running on a different host/port)
API_BASE_URL: str = "http://localhost:8000"
ARBITRATE_ENDPOINT: str = f"{API_BASE_URL}/api/ingest/arbitrate"

# Default seconds between ticks (overridden by --interval CLI arg)
DEFAULT_INTERVAL: int = 8

# Maximum number of connection retries before giving up on a single tick
MAX_RETRIES: int = 3
RETRY_DELAY: float = 2.0  # seconds between retries


# ═══════════════════════════════════════════════════════════════════════
# STATION BASE TEMPERATURES (realistic for Indian late-summer / monsoon)
# ═══════════════════════════════════════════════════════════════════════
# Each station starts at a "true" base temperature that drifts via
# random walk every tick.  T_Predicted is set to this drifting baseline.

STATION_CONFIGS: dict[str, dict] = {
    "AWS-DEL-001": {"name": "New Delhi",           "base_temp": 34.0},
    "AWS-MUM-001": {"name": "Mumbai",              "base_temp": 30.0},
    "AWS-BLR-001": {"name": "Bengaluru",           "base_temp": 24.0},
    "AWS-CHN-001": {"name": "Chennai",             "base_temp": 32.0},
    "AWS-KOL-001": {"name": "Kolkata",             "base_temp": 31.0},
    "AWS-HYD-001": {"name": "Hyderabad",           "base_temp": 29.0},
    "AWS-JAI-001": {"name": "Jaipur",              "base_temp": 35.0},
    "AWS-LKO-001": {"name": "Lucknow",             "base_temp": 33.0},
    "AWS-PAT-001": {"name": "Patna",               "base_temp": 32.0},
    "AWS-GUW-001": {"name": "Guwahati",            "base_temp": 28.0},
    "AWS-TRV-001": {"name": "Thiruvananthapuram",  "base_temp": 29.0},
    "AWS-PNQ-001": {"name": "Pune",                "base_temp": 27.0},
}

# Station IDs in a fixed order for consistent console output
STATION_IDS: list[str] = list(STATION_CONFIGS.keys())


# ═══════════════════════════════════════════════════════════════════════
# SCENARIO SCHEDULE
# ═══════════════════════════════════════════════════════════════════════
# Each scenario injects an anomaly offset starting at a given tick.
#
#   "aws_offset"     → added ONLY to T_AWS      (simulates sensor drift)
#   "witness_offset" → added ONLY to T_Witness   (simulates faulty node)
#   "both_offset"    → added to BOTH T_AWS & T_Witness (real extreme)
#
# Offsets are cumulative with per-tick noise so values feel organic.

SCENARIOS: dict[str, dict] = {
    # PRIMARY_DRIFT – Delhi AWS sensor goes haywire from tick 4
    "AWS-DEL-001": {
        "start_tick": 4,
        "aws_offset": 6.0,       # +6°C on AWS only
        "witness_offset": 0.0,
        "both_offset": 0.0,
        "label": "PRIMARY_DRIFT scenario",
    },
    # WITNESS_FAULT – Mumbai witness node reports garbage from tick 4
    "AWS-MUM-001": {
        "start_tick": 4,
        "aws_offset": 0.0,
        "witness_offset": 7.0,   # +7°C on Witness only
        "both_offset": 0.0,
        "label": "WITNESS_FAULT scenario",
    },
    # TRUE_EXTREME – Chennai real heatwave from tick 6
    "AWS-CHN-001": {
        "start_tick": 6,
        "aws_offset": 0.0,
        "witness_offset": 0.0,
        "both_offset": 8.0,      # +8°C on both sensors
        "label": "TRUE_EXTREME scenario",
    },
}


# ═══════════════════════════════════════════════════════════════════════
# COLOUR HELPERS (ANSI terminal colours for pretty console output)
# ═══════════════════════════════════════════════════════════════════════

class C:
    """ANSI colour codes for terminal output."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    CYAN    = "\033[96m"
    MAGENTA = "\033[95m"
    WHITE   = "\033[97m"
    BG_RED  = "\033[41m"


DECISION_COLOURS: dict[str, str] = {
    "NORMAL":        C.GREEN,
    "PRIMARY_DRIFT": C.RED,
    "WITNESS_FAULT": C.YELLOW,
    "TRUE_EXTREME":  C.BG_RED + C.WHITE,
}


# ═══════════════════════════════════════════════════════════════════════
# SIMULATOR CLASS
# ═══════════════════════════════════════════════════════════════════════

class StationSimulator:
    """
    Drives the temperature simulation loop.

    Maintains a per-station drifting baseline and applies scenario
    offsets at the scheduled tick to produce anomalies.
    """

    def __init__(self, interval: int = DEFAULT_INTERVAL) -> None:
        self.interval: int = interval
        self.tick: int = 0

        # Seed the RNG so scenarios are deterministic and repeatable
        random.seed(42)

        # Store ORIGINAL base temps (immutable reference for clamping)
        self.original_baselines: dict[str, float] = {
            sid: cfg["base_temp"] for sid, cfg in STATION_CONFIGS.items()
        }

        # Mutable copy of base temperatures (random-walked each tick)
        self.baselines: dict[str, float] = dict(self.original_baselines)

    # ── Random walk for baseline drift ───────────────────────────────

    def _drift_baselines(self) -> None:
        """
        Apply a small random walk to every station's baseline.
        Clamped to +-1.0 deg C from the original so that unscripted
        stations never accidentally cross the arbitration thresholds
        (epsilon=2.0, delta=1.5).
        """
        MAX_DRIFT: float = 1.0  # max deviation from original base temp
        for sid in STATION_IDS:
            self.baselines[sid] += random.uniform(-0.2, 0.2)
            # Clamp to prevent runaway drift
            orig = self.original_baselines[sid]
            self.baselines[sid] = max(orig - MAX_DRIFT,
                                      min(orig + MAX_DRIFT,
                                          self.baselines[sid]))

    # ── Generate readings for one station on this tick ───────────────

    def generate_readings(self, station_id: str) -> dict:
        """
        Produce t_aws, t_witness, t_predicted for a station.

        Returns a dict ready to POST to /api/ingest/arbitrate.
        """
        base: float = self.baselines[station_id]

        # T_Predicted = the slow-drifting baseline (truth reference)
        t_predicted: float = round(base, 2)

        # Default: both sensors read close to truth + SMALL noise
        # Kept at +-0.15 deg C so that |AWS-Witness| stays well below
        # epsilon=2.0 and |sensor-predicted| stays below delta=1.5
        # for all unscripted (NORMAL) stations.
        noise_aws: float = random.uniform(-0.15, 0.15)
        noise_wit: float = random.uniform(-0.15, 0.15)
        t_aws: float = base + noise_aws
        t_witness: float = base + noise_wit

        # ── Apply scenario offsets if active ─────────────────────────
        scenario = SCENARIOS.get(station_id)
        if scenario and self.tick >= scenario["start_tick"]:
            aws_off: float = scenario["aws_offset"] + scenario["both_offset"]
            wit_off: float = scenario["witness_offset"] + scenario["both_offset"]
            t_aws     += aws_off
            t_witness += wit_off
            # Debug: confirm exactly which station_id is being modified
            print(
                f"  {C.DIM}[DEBUG] Applying scenario to "
                f"{station_id}: T_AWS += {aws_off}, "
                f"T_WIT += {wit_off}{C.RESET}"
            )

        return {
            "station_id": station_id,
            "t_aws": round(t_aws, 2),
            "t_witness": round(t_witness, 2),
            "t_predicted": t_predicted,
        }

    # ── POST a reading to the backend ────────────────────────────────

    async def post_reading(
        self,
        client: httpx.AsyncClient,
        payload: dict,
    ) -> Optional[dict]:
        """
        Send an arbitration request to the backend.
        Returns the JSON response dict, or None on failure.
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await client.post(ARBITRATE_ENDPOINT, json=payload)
                resp.raise_for_status()
                return resp.json()
            except httpx.ConnectError:
                if attempt < MAX_RETRIES:
                    print(
                        f"  {C.YELLOW}[!] Backend not reachable "
                        f"(attempt {attempt}/{MAX_RETRIES}), "
                        f"retrying in {RETRY_DELAY}s...{C.RESET}"
                    )
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    print(
                        f"  {C.RED}[X] Backend unreachable after "
                        f"{MAX_RETRIES} attempts. Is uvicorn running "
                        f"on {API_BASE_URL}?{C.RESET}"
                    )
                    return None
            except httpx.HTTPStatusError as exc:
                print(
                    f"  {C.RED}[X] HTTP {exc.response.status_code} "
                    f"for {payload['station_id']}: "
                    f"{exc.response.text[:200]}{C.RESET}"
                )
                return None
            except Exception as exc:
                print(f"  {C.RED}[X] Unexpected error: {exc}{C.RESET}")
                return None
        return None

    # ── Pretty-print one station result ──────────────────────────────

    @staticmethod
    def log_result(payload: dict, response: Optional[dict]) -> None:
        """Print a formatted console line for one station's tick."""
        sid = payload["station_id"]
        city = STATION_CONFIGS[sid]["name"]

        t_aws = payload["t_aws"]
        t_wit = payload["t_witness"]
        t_pred = payload["t_predicted"]

        if response:
            decision = response.get("decision", "???")
            colour = DECISION_COLOURS.get(decision, C.WHITE)
            severity = response.get("severity", "")
        else:
            decision = "NO_RESPONSE"
            colour = C.DIM
            severity = ""

        sev_tag = f" [{severity}]" if severity else ""

        print(
            f"  {C.CYAN}{sid}{C.RESET}  "
            f"{city:<22s}  "
            f"AWS={t_aws:6.2f}  "
            f"WIT={t_wit:6.2f}  "
            f"PRED={t_pred:6.2f}  >>  "
            f"{colour}{C.BOLD}{decision}{C.RESET}"
            f"{C.DIM}{sev_tag}{C.RESET}"
        )

    # ── Main simulation loop ─────────────────────────────────────────

    async def run(self) -> None:
        """Run the simulation loop indefinitely."""
        print(f"\n{C.BOLD}{'=' * 72}{C.RESET}")
        print(
            f"{C.BOLD}{C.MAGENTA}"
            f"  The Witness Network -- Station Simulator"
            f"{C.RESET}"
        )
        print(f"{C.BOLD}{'=' * 72}{C.RESET}")
        print(f"  Target   : {ARBITRATE_ENDPOINT}")
        print(f"  Stations : {len(STATION_IDS)}")
        print(f"  Interval : {self.interval}s per tick")
        print(f"  Scenarios: Delhi -> PRIMARY_DRIFT (tick 4)")
        print(f"             Mumbai -> WITNESS_FAULT (tick 4)")
        print(f"             Chennai -> TRUE_EXTREME (tick 6)")
        print(f"{C.BOLD}{'=' * 72}{C.RESET}\n")

        async with httpx.AsyncClient(timeout=10.0) as client:
            while True:
                self.tick += 1
                now = datetime.now().strftime("%H:%M:%S")

                # ── Announce tick ────────────────────────────────
                print(
                    f"{C.BOLD}{'-' * 72}{C.RESET}\n"
                    f"  {C.BOLD}TICK {self.tick}{C.RESET}  "
                    f"{C.DIM}@ {now}{C.RESET}\n"
                    f"{C.BOLD}{'-' * 72}{C.RESET}"
                )

                # Flag any scenarios becoming active on this tick
                for sid, sc in SCENARIOS.items():
                    if self.tick == sc["start_tick"]:
                        city = STATION_CONFIGS[sid]["name"]
                        print(
                            f"  {C.MAGENTA}>> Scenario activated: "
                            f"{city} ({sid}) -> {sc['label']}{C.RESET}"
                        )

                # ── Drift baselines before generating readings ───
                self._drift_baselines()

                # ── Send readings for all 12 stations ────────────
                for sid in STATION_IDS:
                    payload = self.generate_readings(sid)
                    response = await self.post_reading(client, payload)
                    self.log_result(payload, response)

                print()  # blank line after each tick

                # ── Wait for next tick ───────────────────────────
                await asyncio.sleep(self.interval)


# ═══════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Simulate weather station data for The Witness Network.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/simulate_stations.py\n"
            "  python scripts/simulate_stations.py --interval 5\n"
            "  python scripts/simulate_stations.py --reset\n"
        ),
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=DEFAULT_INTERVAL,
        help=f"Seconds between ticks (default: {DEFAULT_INTERVAL})",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="(Placeholder) Reset backend data before starting simulation.",
    )
    return parser.parse_args()


async def main() -> None:
    """Entry point for the simulator."""
    args = parse_args()

    # ── Handle --reset flag (placeholder) ────────────────────────────
    if args.reset:
        print(
            f"\n{C.YELLOW}{C.BOLD}"
            f"  [!] --reset flag detected.{C.RESET}\n"
            f"  {C.YELLOW}This is a placeholder. In a future version, "
            f"this will clear anomaly_events\n"
            f"  and sensor_readings tables via a dedicated backend "
            f"endpoint before starting.\n"
            f"  For now, proceeding with simulation as normal.{C.RESET}\n"
        )

    simulator = StationSimulator(interval=args.interval)

    try:
        await simulator.run()
    except KeyboardInterrupt:
        print(f"\n{C.BOLD}{C.MAGENTA}  [STOP] Simulator stopped.{C.RESET}\n")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
