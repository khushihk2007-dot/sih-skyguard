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

/* ─── Station with geo-coordinates (for map rendering) ─── */
export interface Station {
  id: string;
  name: string;
  lat: number;
  lng: number;
  status: AnomalyDecision;
  t_aws: number;
  t_witness: number;
  t_predicted: number;
  lastSeen: string;
  totalReadings: number;
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
  decision: AnomalyDecision;
  reason: string;
  severity: Severity;
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
  t_aws: number;
  t_witness: number;
  t_predicted: number;
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
  color: string;
  glow: string;
  icon: string;
  dotClass: string;
}

/** Mapping from decision types to UI presentation */
export const DECISION_META: Record<AnomalyDecision, DecisionMeta> = {
  NORMAL: {
    label: "Normal",
    color: "#22c55e",
    glow: "rgba(34, 197, 94, 0.15)",
    icon: "✓",
    dotClass: "normal",
  },
  PRIMARY_DRIFT: {
    label: "Primary Drift",
    color: "#f59e0b",
    glow: "rgba(245, 158, 11, 0.15)",
    icon: "⚠",
    dotClass: "drift",
  },
  WITNESS_FAULT: {
    label: "Witness Fault",
    color: "#ef4444",
    glow: "rgba(239, 68, 68, 0.15)",
    icon: "✕",
    dotClass: "fault",
  },
  TRUE_EXTREME: {
    label: "True Extreme",
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
