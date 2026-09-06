/**
 * The Witness Network – API Service Layer
 * =========================================
 * Centralised HTTP client for communicating with the FastAPI backend.
 * Falls back to rich demo data when the backend is unavailable,
 * so the dashboard can always render a compelling demo.
 *
 * Every fetch function returns `{ data, live }` so the UI can show
 * a "Live" vs "Demo" indicator in the header.
 */

import axios from "axios";
import type {
  AnomalyDecision,
  AnomalyTicket,
  ArbitrationRequest,
  ArbitrationResponse,
  ChartDataPoint,
  Severity,
  Station,
  TicketSummary,
} from "../types";

/* ─── Axios instance with base URL ─── */
const api = axios.create({
  baseURL: "/api",
  timeout: 10000,
  headers: { "Content-Type": "application/json" },
});

/* ═══════════════════════════════════════════════════════════════════
   DEMO DATA – realistic Indian weather stations for showcasing
   ═══════════════════════════════════════════════════════════════════ */

const DEMO_STATIONS: Station[] = [
  { id: "AWS-DEL-001", name: "New Delhi – Safdarjung",  lat: 28.5849, lng: 77.2083, status: "NORMAL",        severity: "LOW", t_aws: 34.2, t_witness: 34.0, t_predicted: 33.8, neighbours_used: 2, is_imputed: false, t_imputed: null, original_t_aws: 34.2, reason: null, lastUpdated: null },
  { id: "AWS-MUM-001", name: "Mumbai – Colaba",         lat: 18.9067, lng: 72.8147, status: "PRIMARY_DRIFT", severity: "HIGH", t_aws: 38.7, t_witness: 31.5, t_predicted: 31.2, neighbours_used: 1, is_imputed: true, t_imputed: 31.4, original_t_aws: 38.7, reason: "Official AWS sensor has drifted.", lastUpdated: new Date().toISOString() },
  { id: "AWS-BLR-001", name: "Bengaluru – HAL Airport",  lat: 12.9499, lng: 77.6681, status: "NORMAL",        severity: "LOW", t_aws: 26.1, t_witness: 26.4, t_predicted: 26.0, neighbours_used: 2, is_imputed: false, t_imputed: null, original_t_aws: 26.1, reason: null, lastUpdated: null },
  { id: "AWS-CHN-001", name: "Chennai – Nungambakkam",   lat: 13.0604, lng: 80.2496, status: "TRUE_EXTREME",  severity: "CRITICAL", t_aws: 42.3, t_witness: 42.1, t_predicted: 36.5, neighbours_used: 2, is_imputed: false, t_imputed: null, original_t_aws: 42.3, reason: "Genuine extreme heatwave detected.", lastUpdated: new Date().toISOString() },
  { id: "AWS-KOL-001", name: "Kolkata – Dum Dum",        lat: 22.6520, lng: 88.4463, status: "WITNESS_FAULT", severity: "HIGH", t_aws: 33.0, t_witness: 41.2, t_predicted: 32.8, neighbours_used: 1, is_imputed: false, t_imputed: null, original_t_aws: 33.0, reason: "Witness node is faulty.", lastUpdated: new Date().toISOString() },
  { id: "AWS-HYD-001", name: "Hyderabad – Begumpet",     lat: 17.4432, lng: 78.4674, status: "NORMAL",        severity: "LOW", t_aws: 30.5, t_witness: 30.3, t_predicted: 30.1, neighbours_used: 2, is_imputed: false, t_imputed: null, original_t_aws: 30.5, reason: null, lastUpdated: null },
  { id: "AWS-JAI-001", name: "Jaipur – Sanganer",        lat: 26.8242, lng: 75.8123, status: "NORMAL",        severity: "LOW", t_aws: 36.8, t_witness: 36.5, t_predicted: 36.2, neighbours_used: 2, is_imputed: false, t_imputed: null, original_t_aws: 36.8, reason: null, lastUpdated: null },
  { id: "AWS-LKO-001", name: "Lucknow – Amausi",         lat: 26.7606, lng: 80.8893, status: "PRIMARY_DRIFT", severity: "MEDIUM", t_aws: 40.1, t_witness: 35.4, t_predicted: 35.0, neighbours_used: 2, is_imputed: true, t_imputed: 35.2, original_t_aws: 40.1, reason: "AWS sensor drifted.", lastUpdated: new Date().toISOString() },
  { id: "AWS-PAT-001", name: "Patna – Bihar Sharif",     lat: 25.6093, lng: 85.1376, status: "NORMAL",        severity: "LOW", t_aws: 33.7, t_witness: 33.5, t_predicted: 33.2, neighbours_used: 2, is_imputed: false, t_imputed: null, original_t_aws: 33.7, reason: null, lastUpdated: null },
  { id: "AWS-GUW-001", name: "Guwahati – Borjhar",       lat: 26.1013, lng: 91.5860, status: "TRUE_EXTREME",  severity: "CRITICAL", t_aws: 38.9, t_witness: 39.1, t_predicted: 32.0, neighbours_used: 1, is_imputed: false, t_imputed: null, original_t_aws: 38.9, reason: "Extreme event detected.", lastUpdated: new Date().toISOString() },
  { id: "AWS-TRV-001", name: "Thiruvananthapuram",       lat: 8.5241,  lng: 76.9366, status: "NORMAL",        severity: "LOW", t_aws: 29.8, t_witness: 29.6, t_predicted: 29.5, neighbours_used: 1, is_imputed: false, t_imputed: null, original_t_aws: 29.8, reason: null, lastUpdated: null },
  { id: "AWS-PNQ-001", name: "Pune – Lohegaon",          lat: 18.5822, lng: 73.9197, status: "NORMAL",        severity: "LOW", t_aws: 28.4, t_witness: 28.2, t_predicted: 28.0, neighbours_used: 1, is_imputed: false, t_imputed: null, original_t_aws: 28.4, reason: null, lastUpdated: null },
];

const DEMO_TICKETS: AnomalyTicket[] = [
  {
    id: 1, station_id: "AWS-MUM-001", t_aws: 38.7, t_witness: 31.5, t_predicted: 31.2,
    decision: "PRIMARY_DRIFT", reason: "Official AWS sensor has drifted or failed. |AWS−Witness|=7.20°C exceeds ε=2.00°C, while |Witness−Predicted|=0.30°C is within δ=1.50°C.",
    severity: "HIGH", confidence: 92.5, is_imputed: true, t_imputed: 31.4, original_t_aws: 38.7,
    diff_aws_witness: 7.2, diff_witness_pred: 0.3, diff_aws_pred: 7.5,
    epsilon_used: 2.0, delta_used: 1.5, detected_at: new Date(Date.now() - 120000).toISOString(),
  },
  {
    id: 2, station_id: "AWS-KOL-001", t_aws: 33.0, t_witness: 41.2, t_predicted: 32.8,
    decision: "WITNESS_FAULT", reason: "Witness node is faulty. Official data is still valid. |AWS−Witness|=8.20°C exceeds ε=2.00°C, while |AWS−Predicted|=0.20°C is within δ=1.50°C.",
    severity: "HIGH", confidence: 88.0, is_imputed: false, t_imputed: null, original_t_aws: 33.0,
    diff_aws_witness: 8.2, diff_witness_pred: 8.4, diff_aws_pred: 0.2,
    epsilon_used: 2.0, delta_used: 1.5, detected_at: new Date(Date.now() - 300000).toISOString(),
  },
  {
    id: 3, station_id: "AWS-CHN-001", t_aws: 42.3, t_witness: 42.1, t_predicted: 36.5,
    decision: "TRUE_EXTREME", reason: "Genuine extreme microclimate detected. Both sensors agree (|AWS−Witness|=0.20°C < δ=1.50°C) but deviate from prediction.",
    severity: "CRITICAL", confidence: 95.0, is_imputed: false, t_imputed: null, original_t_aws: 42.3,
    diff_aws_witness: 0.2, diff_witness_pred: 5.6, diff_aws_pred: 5.8,
    epsilon_used: 2.0, delta_used: 1.5, detected_at: new Date(Date.now() - 600000).toISOString(),
  },
  {
    id: 4, station_id: "AWS-GUW-001", t_aws: 38.9, t_witness: 39.1, t_predicted: 32.0,
    decision: "TRUE_EXTREME", reason: "Genuine extreme microclimate detected. Both sensors agree but deviate from prediction baseline.",
    severity: "CRITICAL", confidence: 94.0, is_imputed: false, t_imputed: null, original_t_aws: 38.9,
    diff_aws_witness: 0.2, diff_witness_pred: 7.1, diff_aws_pred: 6.9,
    epsilon_used: 2.0, delta_used: 1.5, detected_at: new Date(Date.now() - 900000).toISOString(),
  },
  {
    id: 5, station_id: "AWS-LKO-001", t_aws: 40.1, t_witness: 35.4, t_predicted: 35.0,
    decision: "PRIMARY_DRIFT", reason: "Official AWS sensor has drifted or failed. |AWS−Witness|=4.70°C exceeds ε=2.00°C.",
    severity: "MEDIUM", confidence: 85.0, is_imputed: true, t_imputed: 35.2, original_t_aws: 40.1,
    diff_aws_witness: 4.7, diff_witness_pred: 0.4, diff_aws_pred: 5.1,
    epsilon_used: 2.0, delta_used: 1.5, detected_at: new Date(Date.now() - 1800000).toISOString(),
  },
  {
    id: 6, station_id: "AWS-DEL-001", t_aws: 34.2, t_witness: 34.0, t_predicted: 33.8,
    decision: "NORMAL", reason: "All readings are consistent.",
    severity: "LOW", confidence: 98.0, is_imputed: false, t_imputed: null, original_t_aws: 34.2,
    diff_aws_witness: 0.2, diff_witness_pred: 0.2, diff_aws_pred: 0.4,
    epsilon_used: 2.0, delta_used: 1.5, detected_at: new Date(Date.now() - 2400000).toISOString(),
  },
];

/* ═══════════════════════════════════════════════════════════════════
   API FUNCTIONS – try real backend, fall back to demo data
   ═══════════════════════════════════════════════════════════════════ */

/**
 * Fetch live station status from GET /api/stations/status.
 * Maps the backend response into the frontend Station type.
 * Returns { data, live } so the UI can show connectivity state.
 *
 * Live = true  → 200 OK from backend, real data shown
 * Live = false → network error / non-200, DEMO_STATIONS used
 */
export async function fetchStations(): Promise<{ data: Station[]; live: boolean }> {
  console.log("[WitnessNet] Fetching stations from /api/stations/status ...");
  try {
    const res = await api.get("/stations/status");

    // Backend returns a direct array: [{ station_id, name, latitude, ... }, ...]
    const raw: any[] = Array.isArray(res.data) ? res.data : [];

    console.log(`[WitnessNet] API Success – ${raw.length} stations received – using live data`);

    // Map every station regardless of whether temps exist yet (fresh DB = all NORMAL)
    const stations: Station[] = raw.map((s) => ({
      id: s.station_id,
      name: s.name,
      lat: s.latitude,
      lng: s.longitude,
      status: (s.decision ?? "NORMAL") as AnomalyDecision,
      severity: (s.severity ?? "LOW") as Severity,
      t_aws: s.t_aws ?? null,
      t_witness: s.t_witness ?? null,
      t_predicted: s.t_predicted ?? null,
      neighbours_used: s.neighbours_used != null ? Number(s.neighbours_used) : null,
      is_imputed: s.is_imputed ?? false,
      t_imputed: s.t_imputed ?? null,
      original_t_aws: s.original_t_aws ?? null,
      reason: s.reason ?? null,
      lastUpdated: s.last_updated ?? null,
    }));

    // Always return live: true when the HTTP call succeeded (even 0 stations on empty DB)
    return { data: stations.length > 0 ? stations : DEMO_STATIONS, live: stations.length > 0 };
  } catch (err: any) {
    console.warn("[WitnessNet] API Failed – falling back to demo data. Reason:", err?.message ?? err);
  }
  return { data: DEMO_STATIONS, live: false };
}

/** Fetch ticket list */
export async function fetchTickets(
  limit = 20,
): Promise<{ data: AnomalyTicket[]; live: boolean }> {
  console.log("[WitnessNet] Fetching tickets from /api/tickets ...");
  try {
    const res = await api.get("/tickets", { params: { limit } });
    const tickets: AnomalyTicket[] = res.data?.tickets ?? [];
    console.log(`[WitnessNet] Tickets – ${tickets.length} received`);
    // Return live data even if 0 tickets (e.g. fresh DB before simulator starts)
    return { data: tickets.length > 0 ? tickets : DEMO_TICKETS, live: true };
  } catch (err: any) {
    console.warn("[WitnessNet] Tickets API Failed – falling back to demo. Reason:", err?.message ?? err);
  }
  return { data: DEMO_TICKETS, live: false };
}

/** Fetch ticket summary */
export async function fetchTicketSummary(): Promise<TicketSummary> {
  try {
    const res = await api.get("/tickets/summary");
    if (res.data?.total_tickets > 0) {
      return res.data;
    }
  } catch {
    // Fall back
  }

  // Compute from demo data
  const byDecision: Record<string, number> = {};
  const bySeverity: Record<string, number> = {};
  DEMO_TICKETS.forEach((t) => {
    byDecision[t.decision] = (byDecision[t.decision] || 0) + 1;
    bySeverity[t.severity] = (bySeverity[t.severity] || 0) + 1;
  });
  return {
    total_tickets: DEMO_TICKETS.length,
    by_decision: byDecision,
    by_severity: bySeverity,
  };
}

/**
 * Fetch chart data for a station from real sensor readings + anomaly events.
 *
 * Strategy:
 *   1. Fetch AWS readings and WITNESS readings in parallel.
 *   2. Fetch recent anomaly events (tickets) for t_predicted values.
 *   3. Pair readings by `recorded_at` timestamp into ChartDataPoint rows.
 *   4. Return empty array if no real data exists (no fake data generated).
 */
export async function fetchStationChart(
  stationId: string,
): Promise<ChartDataPoint[]> {
  try {
    // Fetch AWS readings, WITNESS readings, and anomaly events in parallel
    const [awsRes, witRes, ticketsRes] = await Promise.all([
      api.get(`/stations/${stationId}/readings`, {
        params: { source: "AWS", limit: 50 },
      }),
      api.get(`/stations/${stationId}/readings`, {
        params: { source: "WITNESS", limit: 50 },
      }),
      api.get("/tickets", {
        params: { station_id: stationId, limit: 50 },
      }),
    ]);

    const awsReadings: any[] = awsRes.data?.readings ?? [];
    const witReadings: any[] = witRes.data?.readings ?? [];
    const tickets: any[] = ticketsRes.data?.tickets ?? [];

    if (awsReadings.length === 0 && witReadings.length === 0) {
      // No real readings yet – return empty (clean empty state)
      return [];
    }

    // Build lookup maps keyed by recorded_at ISO string.
    // The simulator persists AWS and WITNESS readings with the same
    // recorded_at timestamp per tick, so they pair naturally.
    const awsByTime = new Map<string, number>();
    for (const r of awsReadings) {
      awsByTime.set(r.recorded_at, r.temperature);
    }

    const witByTime = new Map<string, number>();
    for (const r of witReadings) {
      witByTime.set(r.recorded_at, r.temperature);
    }

    // Build predicted lookup from anomaly events (keyed by detected_at)
    const predByTime = new Map<string, number>();
    for (const t of tickets) {
      if (t.detected_at && t.t_predicted != null) {
        predByTime.set(t.detected_at, t.t_predicted);
      }
    }

    // Collect all unique timestamps and sort chronologically
    const allTimes = new Set<string>([
      ...awsByTime.keys(),
      ...witByTime.keys(),
    ]);
    const sortedTimes = Array.from(allTimes).sort(
      (a, b) => new Date(a).getTime() - new Date(b).getTime(),
    );

    // Build chart data points by pairing readings at each timestamp
    const points: ChartDataPoint[] = sortedTimes.map((ts) => {
      const awsTemp = awsByTime.get(ts);
      const witTemp = witByTime.get(ts);
      const predTemp = predByTime.get(ts);

      return {
        time: new Date(ts).toLocaleTimeString("en-IN", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }),
        t_aws: awsTemp ?? (witTemp ?? 0),
        t_witness: witTemp ?? (awsTemp ?? 0),
        t_predicted: predTemp ?? (awsTemp ?? (witTemp ?? 0)),
      };
    });

    return points;
  } catch (err) {
    console.warn("[WitnessNet] Chart data fetch failed:", err);
  }

  // No real data available – return empty array (clean empty state)
  return [];
}

/** Run manual arbitration */
export async function runArbitration(
  payload: ArbitrationRequest,
): Promise<ArbitrationResponse> {
  const res = await api.post("/ingest/arbitrate", payload);
  return res.data;
}

export default api;
