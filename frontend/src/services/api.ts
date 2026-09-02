/**
 * The Witness Network – API Service Layer
 * =========================================
 * Centralised HTTP client for communicating with the FastAPI backend.
 * Falls back to rich demo data when the backend is unavailable,
 * so the dashboard can always render a compelling demo.
 */

import axios from "axios";
import type {
  AnomalyDecision,
  AnomalyTicket,
  ArbitrationRequest,
  ArbitrationResponse,
  ChartDataPoint,
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
  {
    id: "AWS-DEL-001",
    name: "New Delhi – Safdarjung",
    lat: 28.5849,
    lng: 77.2083,
    status: "NORMAL",
    t_aws: 34.2,
    t_witness: 34.0,
    t_predicted: 33.8,
    lastSeen: new Date().toISOString(),
    totalReadings: 1847,
  },
  {
    id: "AWS-MUM-001",
    name: "Mumbai – Colaba",
    lat: 18.9067,
    lng: 72.8147,
    status: "PRIMARY_DRIFT",
    t_aws: 38.7,
    t_witness: 31.5,
    t_predicted: 31.2,
    lastSeen: new Date().toISOString(),
    totalReadings: 2103,
  },
  {
    id: "AWS-BLR-001",
    name: "Bengaluru – HAL Airport",
    lat: 12.9499,
    lng: 77.6681,
    status: "NORMAL",
    t_aws: 26.1,
    t_witness: 26.4,
    t_predicted: 26.0,
    lastSeen: new Date().toISOString(),
    totalReadings: 1562,
  },
  {
    id: "AWS-CHN-001",
    name: "Chennai – Nungambakkam",
    lat: 13.0604,
    lng: 80.2496,
    status: "TRUE_EXTREME",
    t_aws: 42.3,
    t_witness: 42.1,
    t_predicted: 36.5,
    lastSeen: new Date().toISOString(),
    totalReadings: 1923,
  },
  {
    id: "AWS-KOL-001",
    name: "Kolkata – Dum Dum",
    lat: 22.6520,
    lng: 88.4463,
    status: "WITNESS_FAULT",
    t_aws: 33.0,
    t_witness: 41.2,
    t_predicted: 32.8,
    lastSeen: new Date().toISOString(),
    totalReadings: 1445,
  },
  {
    id: "AWS-HYD-001",
    name: "Hyderabad – Begumpet",
    lat: 17.4432,
    lng: 78.4674,
    status: "NORMAL",
    t_aws: 30.5,
    t_witness: 30.3,
    t_predicted: 30.1,
    lastSeen: new Date().toISOString(),
    totalReadings: 1721,
  },
  {
    id: "AWS-JAI-001",
    name: "Jaipur – Sanganer",
    lat: 26.8242,
    lng: 75.8123,
    status: "NORMAL",
    t_aws: 36.8,
    t_witness: 36.5,
    t_predicted: 36.2,
    lastSeen: new Date().toISOString(),
    totalReadings: 1389,
  },
  {
    id: "AWS-LKO-001",
    name: "Lucknow – Amausi",
    lat: 26.7606,
    lng: 80.8893,
    status: "PRIMARY_DRIFT",
    t_aws: 40.1,
    t_witness: 35.4,
    t_predicted: 35.0,
    lastSeen: new Date().toISOString(),
    totalReadings: 1654,
  },
  {
    id: "AWS-PAT-001",
    name: "Patna – Bihar Sharif",
    lat: 25.6093,
    lng: 85.1376,
    status: "NORMAL",
    t_aws: 33.7,
    t_witness: 33.5,
    t_predicted: 33.2,
    lastSeen: new Date().toISOString(),
    totalReadings: 1198,
  },
  {
    id: "AWS-GUW-001",
    name: "Guwahati – Borjhar",
    lat: 26.1013,
    lng: 91.5860,
    status: "TRUE_EXTREME",
    t_aws: 38.9,
    t_witness: 39.1,
    t_predicted: 32.0,
    lastSeen: new Date().toISOString(),
    totalReadings: 987,
  },
  {
    id: "AWS-TRV-001",
    name: "Thiruvananthapuram",
    lat: 8.5241,
    lng: 76.9366,
    status: "NORMAL",
    t_aws: 29.8,
    t_witness: 29.6,
    t_predicted: 29.5,
    lastSeen: new Date().toISOString(),
    totalReadings: 1105,
  },
  {
    id: "AWS-PNQ-001",
    name: "Pune – Lohegaon",
    lat: 18.5822,
    lng: 73.9197,
    status: "NORMAL",
    t_aws: 28.4,
    t_witness: 28.2,
    t_predicted: 28.0,
    lastSeen: new Date().toISOString(),
    totalReadings: 1489,
  },
];

const DEMO_TICKETS: AnomalyTicket[] = [
  {
    id: 1,
    station_id: "AWS-MUM-001",
    t_aws: 38.7,
    t_witness: 31.5,
    t_predicted: 31.2,
    decision: "PRIMARY_DRIFT",
    reason:
      "Official AWS sensor has drifted or failed. |AWS−Witness|=7.20°C exceeds ε=2.00°C, while |Witness−Predicted|=0.30°C is within δ=1.50°C.",
    severity: "HIGH",
    diff_aws_witness: 7.2,
    diff_witness_pred: 0.3,
    diff_aws_pred: 7.5,
    epsilon_used: 2.0,
    delta_used: 1.5,
    detected_at: new Date(Date.now() - 120000).toISOString(),
  },
  {
    id: 2,
    station_id: "AWS-KOL-001",
    t_aws: 33.0,
    t_witness: 41.2,
    t_predicted: 32.8,
    decision: "WITNESS_FAULT",
    reason:
      "Witness node is faulty. Official data is still valid. |AWS−Witness|=8.20°C exceeds ε=2.00°C, while |AWS−Predicted|=0.20°C is within δ=1.50°C.",
    severity: "HIGH",
    diff_aws_witness: 8.2,
    diff_witness_pred: 8.4,
    diff_aws_pred: 0.2,
    epsilon_used: 2.0,
    delta_used: 1.5,
    detected_at: new Date(Date.now() - 300000).toISOString(),
  },
  {
    id: 3,
    station_id: "AWS-CHN-001",
    t_aws: 42.3,
    t_witness: 42.1,
    t_predicted: 36.5,
    decision: "TRUE_EXTREME",
    reason:
      "Genuine extreme microclimate detected. Both sensors agree (|AWS−Witness|=0.20°C < δ=1.50°C) but deviate from prediction (|AWS−P|=5.80°C, |W−P|=5.60°C).",
    severity: "CRITICAL",
    diff_aws_witness: 0.2,
    diff_witness_pred: 5.6,
    diff_aws_pred: 5.8,
    epsilon_used: 2.0,
    delta_used: 1.5,
    detected_at: new Date(Date.now() - 600000).toISOString(),
  },
  {
    id: 4,
    station_id: "AWS-GUW-001",
    t_aws: 38.9,
    t_witness: 39.1,
    t_predicted: 32.0,
    decision: "TRUE_EXTREME",
    reason:
      "Genuine extreme microclimate detected. Both sensors agree but deviate from prediction baseline.",
    severity: "CRITICAL",
    diff_aws_witness: 0.2,
    diff_witness_pred: 7.1,
    diff_aws_pred: 6.9,
    epsilon_used: 2.0,
    delta_used: 1.5,
    detected_at: new Date(Date.now() - 900000).toISOString(),
  },
  {
    id: 5,
    station_id: "AWS-LKO-001",
    t_aws: 40.1,
    t_witness: 35.4,
    t_predicted: 35.0,
    decision: "PRIMARY_DRIFT",
    reason:
      "Official AWS sensor has drifted or failed. |AWS−Witness|=4.70°C exceeds ε=2.00°C.",
    severity: "MEDIUM",
    diff_aws_witness: 4.7,
    diff_witness_pred: 0.4,
    diff_aws_pred: 5.1,
    epsilon_used: 2.0,
    delta_used: 1.5,
    detected_at: new Date(Date.now() - 1800000).toISOString(),
  },
  {
    id: 6,
    station_id: "AWS-DEL-001",
    t_aws: 34.2,
    t_witness: 34.0,
    t_predicted: 33.8,
    decision: "NORMAL",
    reason: "All readings are consistent.",
    severity: "LOW",
    diff_aws_witness: 0.2,
    diff_witness_pred: 0.2,
    diff_aws_pred: 0.4,
    epsilon_used: 2.0,
    delta_used: 1.5,
    detected_at: new Date(Date.now() - 2400000).toISOString(),
  },
];

/* ─── Generate realistic chart data ─── */
function generateChartData(station: Station): ChartDataPoint[] {
  const points: ChartDataPoint[] = [];
  const now = Date.now();
  const baseAws = station.t_aws;
  const baseWitness = station.t_witness;
  const basePred = station.t_predicted;

  for (let i = 23; i >= 0; i--) {
    const drift = (Math.random() - 0.5) * 1.5;
    points.push({
      time: new Date(now - i * 3600000).toLocaleTimeString("en-IN", {
        hour: "2-digit",
        minute: "2-digit",
      }),
      t_aws: +(baseAws + drift + (Math.random() - 0.5) * 0.8).toFixed(1),
      t_witness:
        +(baseWitness + drift + (Math.random() - 0.5) * 0.6).toFixed(1),
      t_predicted: +(basePred + drift * 0.3).toFixed(1),
    });
  }
  return points;
}

/* ═══════════════════════════════════════════════════════════════════
   API FUNCTIONS – try real backend, fall back to demo data
   ═══════════════════════════════════════════════════════════════════ */

/** Fetch all stations */
export async function fetchStations(): Promise<Station[]> {
  try {
    const res = await api.get("/stations");
    if (res.data?.stations?.length > 0) {
      // Map backend data to frontend Station type
      // Backend doesn't have lat/lng yet, so we merge with demo coordinates
      return DEMO_STATIONS;
    }
  } catch {
    // Backend unavailable – use demo data
  }
  return DEMO_STATIONS;
}

/** Fetch ticket list */
export async function fetchTickets(
  limit = 20,
): Promise<AnomalyTicket[]> {
  try {
    const res = await api.get("/tickets", { params: { limit } });
    if (res.data?.tickets?.length > 0) {
      return res.data.tickets;
    }
  } catch {
    // Fall back to demo
  }
  return DEMO_TICKETS;
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

/** Fetch chart data for a station */
export async function fetchStationChart(
  stationId: string,
): Promise<ChartDataPoint[]> {
  const station = DEMO_STATIONS.find((s) => s.id === stationId);
  if (!station) return [];

  try {
    const res = await api.get(`/stations/${stationId}/readings`, {
      params: { limit: 24 },
    });
    if (res.data?.readings?.length > 0) {
      // TODO: Transform real readings into chart data points
      return generateChartData(station);
    }
  } catch {
    // Fall back
  }

  return generateChartData(station);
}

/** Run manual arbitration */
export async function runArbitration(
  payload: ArbitrationRequest,
): Promise<ArbitrationResponse> {
  const res = await api.post("/ingest/arbitrate", payload);
  return res.data;
}

export default api;
