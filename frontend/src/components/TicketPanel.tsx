/**
 * TicketPanel – Recent anomaly tickets feed
 * ============================================
 * Scrollable list of the most recent anomaly events,
 * each showing decision, severity, station, reason,
 * confidence score, and timestamp.
 *
 * Visual improvements (v2):
 *  - Distinct severity badges (LOW → green, MEDIUM → amber,
 *    HIGH → orange, CRITICAL → purple)
 *  - Prominent decision badge with colored pill + icon
 *  - Confidence score chip (color-coded)
 *  - Full reason text (no truncation)
 *  - Selected-station highlight ring
 *  - Hover lift effect + better spacing
 */

import { useEffect, useState } from "react";
import { AlertCircle, Clock, Zap, TrendingUp, Activity } from "lucide-react";
import type { AnomalyTicket } from "../types";
import { DECISION_META } from "../types";
import { fetchTickets } from "../services/api";

/* ── Severity visual config ── */
interface SeverityMeta {
  color: string;
  bg: string;
  border: string;
  icon: string;
  label: string;
}

const SEVERITY_META: Record<string, SeverityMeta> = {
  LOW: {
    color: "#4ade80",
    bg: "rgba(74, 222, 128, 0.10)",
    border: "rgba(74, 222, 128, 0.30)",
    icon: "↓",
    label: "LOW",
  },
  MEDIUM: {
    color: "#fbbf24",
    bg: "rgba(251, 191, 36, 0.12)",
    border: "rgba(251, 191, 36, 0.35)",
    icon: "▲",
    label: "MED",
  },
  HIGH: {
    color: "#fb923c",
    bg: "rgba(251, 146, 60, 0.12)",
    border: "rgba(251, 146, 60, 0.35)",
    icon: "⚠",
    label: "HIGH",
  },
  CRITICAL: {
    color: "#c084fc",
    bg: "rgba(192, 132, 252, 0.12)",
    border: "rgba(192, 132, 252, 0.40)",
    icon: "🔴",
    label: "CRIT",
  },
};

interface TicketPanelProps {
  onSelectStation?: (stationId: string) => void;
  /** ID of the currently selected station (for highlight ring) */
  selectedStationId?: string | null;
}

export default function TicketPanel({
  onSelectStation,
  selectedStationId,
}: TicketPanelProps) {
  const [tickets, setTickets] = useState<AnomalyTicket[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const { data } = await fetchTickets(15);
      if (!cancelled) {
        setTickets(data);
        setLoading(false);
      }
    }

    load();
    const id = setInterval(load, 5_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  /** Format a relative timestamp (e.g. "3m ago") */
  function timeAgo(iso: string): string {
    const diff = Date.now() - new Date(iso).getTime();
    const secs = Math.floor(diff / 1000);
    if (secs < 60) return `${secs}s ago`;
    const mins = Math.floor(secs / 60);
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  }

  const activeCount = tickets.filter((t) => t.decision !== "NORMAL").length;

  return (
    <div
      className="glass-card flex flex-col h-full animate-slide-up"
      style={{ animationDelay: "150ms" }}
    >
      {/* ── Header ── */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-subtle)] shrink-0">
        <div className="flex items-center gap-2">
          <AlertCircle size={14} className="text-[var(--accent-red)]" />
          <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
            Anomaly Tickets
          </h4>
        </div>
        <div className="flex items-center gap-2">
          {activeCount > 0 && (
            <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-[var(--accent-red)]/15 text-[var(--accent-red)] font-bold border border-[var(--accent-red)]/25">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent-red)] pulse-live inline-block" />
              {activeCount} active
            </span>
          )}
          <span className="text-[10px] text-[var(--text-muted)] font-mono">
            {tickets.length} total
          </span>
        </div>
      </div>

      {/* ── Ticket list ── */}
      <div className="flex-1 overflow-y-auto px-2 py-2.5 space-y-2.5">
        {loading ? (
          <div className="flex items-center justify-center h-full gap-2">
            <div className="w-5 h-5 border-2 border-[var(--accent-cyan)] border-t-transparent rounded-full animate-spin" />
            <span className="text-xs text-[var(--text-muted)]">Loading tickets…</span>
          </div>
        ) : tickets.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-[var(--text-muted)]">
            <Activity size={20} className="opacity-40" />
            <span className="text-xs">No tickets found</span>
          </div>
        ) : (
          tickets.map((ticket, i) => (
            <TicketRow
              key={ticket.id}
              ticket={ticket}
              index={i}
              timeAgo={timeAgo}
              onSelectStation={onSelectStation}
              isSelected={selectedStationId === ticket.station_id}
            />
          ))
        )}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────
   Individual Ticket Row
───────────────────────────────────────────────────────── */
function TicketRow({
  ticket,
  index,
  timeAgo,
  onSelectStation,
  isSelected,
}: {
  ticket: AnomalyTicket;
  index: number;
  timeAgo: (iso: string) => string;
  onSelectStation?: (stationId: string) => void;
  isSelected: boolean;
}) {
  const meta = DECISION_META[ticket.decision] ?? DECISION_META.NORMAL;
  const sev = SEVERITY_META[ticket.severity] ?? SEVERITY_META.LOW;

  /* Confidence band */
  const conf = Math.round(ticket.confidence * 100);
  const confColor =
    conf >= 85 ? "#4ade80" : conf >= 65 ? "#fbbf24" : "#fb923c";

  return (
    <div
      className="rounded-xl transition-all duration-200 cursor-pointer animate-fade-in"
      style={{
        background: isSelected
          ? `linear-gradient(135deg, ${meta.color}22, rgba(15, 23, 42, 0.7))`
          : `linear-gradient(135deg, ${meta.color}0D, rgba(15, 23, 42, 0.5))`,
        border: isSelected
          ? `1.5px solid ${meta.color}60`
          : `1px solid ${meta.color}28`,
        boxShadow: isSelected
          ? `0 0 0 2px ${meta.color}22, 0 4px 16px rgba(0,0,0,0.3)`
          : "none",
        padding: "10px 12px",
        animationDelay: `${index * 40}ms`,
        animationFillMode: "backwards",
      }}
      onClick={() => onSelectStation?.(ticket.station_id)}
      onMouseEnter={(e) => {
        if (!isSelected) {
          e.currentTarget.style.background = `linear-gradient(135deg, ${meta.color}1A, rgba(15, 23, 42, 0.65))`;
          e.currentTarget.style.borderColor = `${meta.color}45`;
          e.currentTarget.style.transform = "translateY(-1px)";
          e.currentTarget.style.boxShadow = `0 4px 20px rgba(0,0,0,0.25)`;
        }
      }}
      onMouseLeave={(e) => {
        if (!isSelected) {
          e.currentTarget.style.background = `linear-gradient(135deg, ${meta.color}0D, rgba(15, 23, 42, 0.5))`;
          e.currentTarget.style.borderColor = `${meta.color}28`;
          e.currentTarget.style.transform = "translateY(0)";
          e.currentTarget.style.boxShadow = "none";
        }
      }}
    >
      {/* ── Row 1: Decision badge + Severity badge + Timestamp ── */}
      <div className="flex items-center justify-between mb-2 gap-1">
        <div className="flex items-center gap-1.5 flex-wrap min-w-0">

          {/* Decision pill */}
          <span
            className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-md tracking-wide"
            style={{
              backgroundColor: `${meta.color}1E`,
              color: meta.color,
              border: `1px solid ${meta.color}40`,
            }}
          >
            <span>{meta.icon}</span>
            {meta.label.toUpperCase()}
          </span>

          {/* Severity pill */}
          <span
            className="inline-flex items-center gap-0.5 text-[9.5px] font-bold px-1.5 py-0.5 rounded-md tracking-widest uppercase"
            style={{
              backgroundColor: sev.bg,
              color: sev.color,
              border: `1px solid ${sev.border}`,
            }}
          >
            <span className="text-[8px]">{sev.icon}</span>
            {sev.label}
          </span>

          {/* Imputed badge */}
          {ticket.is_imputed && (
            <span className="inline-flex items-center gap-0.5 text-[9px] px-1.5 py-0.5 rounded-md font-bold uppercase bg-emerald-500/15 text-emerald-400 border border-emerald-500/35 tracking-wide">
              ✦ IMPUTED
            </span>
          )}
        </div>

        {/* Timestamp */}
        <div className="flex items-center gap-1 text-[10px] text-[var(--text-muted)] shrink-0 font-mono">
          <Clock size={9} className="opacity-70" />
          {timeAgo(ticket.detected_at)}
        </div>
      </div>

      {/* ── Row 2: Station ID + Summary + Confidence ── */}
      <div className="flex items-center justify-between mb-1.5 gap-2">
        <span className="font-mono text-[11px] text-[var(--text-primary)] font-bold tracking-tight">
          {ticket.station_id}
        </span>
        <div className="flex items-center gap-1.5 shrink-0">
          {/* Summary label */}
          <span
            className="text-[9.5px] font-semibold"
            style={{ color: `${meta.color}CC` }}
          >
            {meta.summary}
          </span>
          {/* Confidence chip */}
          <span
            className="text-[9px] font-bold font-mono px-1.5 py-0.5 rounded-md inline-flex items-center gap-0.5"
            style={{
              backgroundColor: `${confColor}14`,
              color: confColor,
              border: `1px solid ${confColor}30`,
            }}
          >
            <TrendingUp size={8} />
            {conf}%
          </span>
        </div>
      </div>

      {/* ── Reason block ── */}
      <div className="text-[10px] text-[var(--text-secondary)] leading-relaxed bg-[var(--bg-primary)]/60 px-2.5 py-2 rounded-lg border border-white/[0.06] font-mono mb-2">
        {ticket.reason}
      </div>

      {/* ── Imputed temperature note ── */}
      {ticket.is_imputed && ticket.t_imputed != null && (
        <div className="text-[9.5px] text-emerald-400 font-medium mb-2 bg-emerald-500/10 px-2 py-1.5 rounded-lg border border-emerald-500/25 flex items-center justify-between">
          <span className="flex items-center gap-1">
            <Zap size={9} className="opacity-80" />
            Corrected by spatial imputation
          </span>
          <strong className="text-emerald-300 font-bold font-mono">
            {ticket.t_imputed.toFixed(1)}°C
          </strong>
        </div>
      )}

      {/* ── Delta chips & Spatial Context ── */}
      <div className="flex gap-1.5 flex-wrap items-center">
        <DeltaChip label="ΔAW" value={ticket.diff_aws_witness} />
        <DeltaChip label="ΔAP" value={ticket.diff_aws_pred} />
        <DeltaChip label="ΔWP" value={ticket.diff_witness_pred} />
        {ticket.neighbours_used != null && (
          <span
            className="text-[9px] font-mono px-1.5 py-0.5 rounded-md font-semibold inline-flex items-center gap-1"
            style={{
              backgroundColor: "rgba(168, 85, 247, 0.10)",
              color: "#c084fc",
              border: "1px solid rgba(168, 85, 247, 0.25)",
            }}
            title={`${ticket.neighbours_used} neighbouring stations used for spatial IDW prediction`}
          >
            <span>🌐</span>
            {ticket.neighbours_used} neighbours
          </span>
        )}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────
   Delta value chip (shows signed delta between sensor pairs)
───────────────────────────────────────────────────────── */
function DeltaChip({ label, value }: { label: string; value: number }) {
  const abs = Math.abs(value);
  const isHigh = abs > 2.0;
  const isMed  = abs > 1.0;

  const color  = isHigh ? "#fb923c" : isMed ? "#fbbf24" : "#4ade80";
  const bg     = isHigh
    ? "rgba(251, 146, 60, 0.10)"
    : isMed
    ? "rgba(251, 191, 36, 0.10)"
    : "rgba(74, 222, 128, 0.08)";

  const sign = value > 0 ? "+" : "";

  return (
    <span
      className="text-[9px] font-mono px-1.5 py-0.5 rounded-md font-semibold"
      style={{
        backgroundColor: bg,
        color,
        border: `1px solid ${color}25`,
      }}
    >
      {label}:{sign}{value.toFixed(1)}°
    </span>
  );
}
