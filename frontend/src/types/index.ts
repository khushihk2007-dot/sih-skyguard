/* ── Types for The Witness Network Command Center ── */

/** Possible arbitration decisions from the Three-Way Engine */
export type AnomalyDecision =
  | "PRIMARY_DRIFT"
  | "WITNESS_FAULT"
  | "TRUE_EXTREME"
  | "NORMAL";

/** Severity levels for anomaly tickets */
export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

/** Data source stream identifier */
export type DataSource = "AWS" | "WITNESS";

/* ─── Station with geo-coordinates and live status ─── */
/* Matches the backend GET /api/stations/status response shape */
export interface Station {
  id: string;           // station_id from backend (e.g. "AWS-DEL-001")
  name: string;
  lat: number;          // latitude from backend
  lng: number;          // longitude from backend
  status: AnomalyDecision;  // latest decision (NORMAL by default)
  severity: Severity;        // latest severity
  t_aws: number | null;
  t_witness: number | null;
  t_predicted: number | null;
  neighbours_used?: number | null;
  is_imputed?: boolean;
  t_imputed?: number | null;
  original_t_aws?: number | null;
  reason: string | null;
  lastUpdated: string | null; // ISO datetime of latest anomaly event
}

/* ─── Sensor reading from the API ─── */
export interface SensorReading {
  id: number;
  station_id: string;
  source: DataSource;
  temperature: number;
  humidity: number | null;
  pressure: number | null;
  recorded_at: string;
  received_at: string;
}

/* ─── Anomaly event / ticket ─── */
export interface AnomalyTicket {
  id: number;
  station_id: string;
  t_aws: number;
  t_witness: number;
  t_predicted: number;
  neighbours_used?: number | null;
  decision: AnomalyDecision;
  reason: string;
  severity: Severity;
  confidence: number;
  is_imputed: boolean;
  t_imputed: number | null;
  original_t_aws: number;
  diff_aws_witness: number;
  diff_witness_pred: number;
  diff_aws_pred: number;
  epsilon_used: number;
  delta_used: number;
  detected_at: string;
}

/* ─── Summary statistics from /api/tickets/summary ─── */
export interface TicketSummary {
  total_tickets: number;
  by_decision: Record<string, number>;
  by_severity: Record<string, number>;
}

/* ─── Arbitration request payload ─── */
export interface ArbitrationRequest {
  station_id: string;
  t_aws: number;
  t_witness: number;
  t_predicted?: number;
  epsilon?: number;
  delta?: number;
}

/* ─── Arbitration response ─── */
export interface ArbitrationResponse {
  station_id: string;
  decision: AnomalyDecision;
  reason: string;
  severity: Severity;
  confidence: number;
  t_aws: number;
  t_witness: number;
  t_predicted: number;
  neighbours_used?: number | null;
  is_imputed: boolean;
  t_imputed: number | null;
  original_t_aws: number;
  diff_aws_witness: number;
  diff_witness_pred: number;
  diff_aws_pred: number;
  anomaly_event_id: number | null;
}

/* ─── Chart data point (for time-series graphs) ─── */
export interface ChartDataPoint {
  time: string;
  t_aws: number;
  t_witness: number;
  t_predicted: number;
}

/* ─── Decision UI metadata ─── */
export interface DecisionMeta {
  label: string;
  summary: string;
  color: string;
  glow: string;
  icon: string;
  dotClass: string;
}

/** Mapping from decision types to UI presentation */
export const DECISION_META: Record<AnomalyDecision, DecisionMeta> = {
  NORMAL: {
    label: "Normal",
    summary: "All sensors are consistent",
    color: "#22c55e",
    glow: "rgba(34, 197, 94, 0.15)",
    icon: "✓",
    dotClass: "normal",
  },
  PRIMARY_DRIFT: {
    label: "Primary Drift",
    summary: "Official sensor has drifted",
    color: "#f59e0b",
    glow: "rgba(245, 158, 11, 0.15)",
    icon: "⚠",
    dotClass: "drift",
  },
  WITNESS_FAULT: {
    label: "Witness Fault",
    summary: "Witness node is faulty",
    color: "#ef4444",
    glow: "rgba(239, 68, 68, 0.15)",
    icon: "✕",
    dotClass: "fault",
  },
  TRUE_EXTREME: {
    label: "True Extreme",
    summary: "Genuine extreme weather detected",
    color: "#3b82f6",
    glow: "rgba(59, 130, 246, 0.15)",
    icon: "⚡",
    dotClass: "extreme",
  },
};

/** Severity color mapping */
export const SEVERITY_COLORS: Record<Severity, string> = {
  LOW: "#22c55e",
  MEDIUM: "#f59e0b",
  HIGH: "#f97316",
  CRITICAL: "#ef4444",
};
