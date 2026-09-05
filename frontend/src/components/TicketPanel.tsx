/**
 * TicketPanel – Recent anomaly tickets feed
 * ============================================
 * Scrollable list of the most recent anomaly events,
 * each showing decision, severity, station, reason,
 * and timestamp.
 */

import { useEffect, useState } from "react";
import { AlertCircle, Clock } from "lucide-react";
import type { AnomalyTicket } from "../types";
import { DECISION_META, SEVERITY_COLORS } from "../types";
import { fetchTickets } from "../services/api";

interface TicketPanelProps {
  onSelectStation?: (stationId: string) => void;
}

export default function TicketPanel({ onSelectStation }: TicketPanelProps) {
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

  return (
    <div className="glass-card flex flex-col h-full animate-slide-up" style={{ animationDelay: "150ms" }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-subtle)]">
        <div className="flex items-center gap-2">
          <AlertCircle size={14} className="text-[var(--accent-red)]" />
          <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
            Anomaly Tickets
          </h4>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--accent-red)]/10 text-[var(--accent-red)] font-semibold">
          {tickets.filter((t) => t.decision !== "NORMAL").length} active
        </span>
      </div>

      {/* Ticket list */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1.5">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="w-5 h-5 border-2 border-[var(--accent-cyan)] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : tickets.length === 0 ? (
          <div className="flex items-center justify-center h-full text-[var(--text-muted)] text-xs">
            No tickets found
          </div>
        ) : (
          tickets.map((ticket, i) => (
            <TicketRow
              key={ticket.id}
              ticket={ticket}
              index={i}
              timeAgo={timeAgo}
              onSelectStation={onSelectStation}
            />
          ))
        )}
      </div>
    </div>
  );
}

/** Individual ticket row */
function TicketRow({
  ticket,
  index,
  timeAgo,
  onSelectStation,
}: {
  ticket: AnomalyTicket;
  index: number;
  timeAgo: (iso: string) => string;
  onSelectStation?: (stationId: string) => void;
}) {
  const meta = DECISION_META[ticket.decision] ?? DECISION_META.NORMAL;
  const sevColor = SEVERITY_COLORS[ticket.severity] ?? SEVERITY_COLORS.LOW;

  return (
    <div
      className="p-3 rounded-lg transition-all duration-200 cursor-pointer animate-fade-in"
      style={{
        background: `linear-gradient(135deg, ${meta.color}0B, rgba(15, 23, 42, 0.4))`,
        border: `1px solid ${meta.color}25`,
        animationDelay: `${index * 40}ms`,
        animationFillMode: "backwards",
      }}
      onClick={() => onSelectStation?.(ticket.station_id)}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = `linear-gradient(135deg, ${meta.color}18, rgba(15, 23, 42, 0.6))`;
        e.currentTarget.style.borderColor = `${meta.color}40`;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = `linear-gradient(135deg, ${meta.color}0B, rgba(15, 23, 42, 0.4))`;
        e.currentTarget.style.borderColor = `${meta.color}25`;
      }}
    >
      {/* Top row: decision + severity + time */}
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span
            className="text-xs font-bold"
            style={{ color: meta.color }}
          >
            {meta.icon} {meta.label}
          </span>
          <span
            className="text-[9px] px-1.5 py-0.5 rounded font-semibold uppercase"
            style={{
              backgroundColor: `${sevColor}18`,
              color: sevColor,
            }}
          >
            {ticket.severity}
          </span>
          {ticket.is_imputed && (
            <span className="text-[9px] px-1.5 py-0.5 rounded font-bold uppercase bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
              Imputed
            </span>
          )}
        </div>
        <div className="flex items-center gap-1 text-[10px] text-[var(--text-muted)]">
          <Clock size={10} />
          {timeAgo(ticket.detected_at)}
        </div>
      </div>

      {/* Station ID & 1-line Summary */}
      <div className="flex items-center justify-between text-[11px] mb-1">
        <span className="font-mono text-[var(--text-secondary)] font-semibold">
          {ticket.station_id}
        </span>
        <span className="text-[10px] font-semibold" style={{ color: meta.color }}>
          {meta.summary}
        </span>
      </div>

      {/* Reason (Full text, fully visible without truncation) */}
      <div className="text-[10px] text-[var(--text-secondary)] leading-relaxed bg-[var(--bg-primary)]/50 p-2 rounded border border-white/5 font-mono mb-2">
        {ticket.reason}
      </div>

      {/* Imputation note if ticket was imputed */}
      {ticket.is_imputed && ticket.t_imputed != null && (
        <div className="text-[9.5px] text-emerald-400 font-medium mb-2 bg-emerald-500/10 px-2 py-1 rounded border border-emerald-500/20 flex items-center justify-between">
          <span>Corrected Imputed Temperature</span>
          <strong className="text-emerald-300 font-bold">{ticket.t_imputed.toFixed(1)}°C</strong>
        </div>
      )}

      {/* Delta chips */}
      <div className="flex gap-2">
        <DeltaChip label="ΔAW" value={ticket.diff_aws_witness} />
        <DeltaChip label="ΔAP" value={ticket.diff_aws_pred} />
        <DeltaChip label="ΔWP" value={ticket.diff_witness_pred} />
      </div>
    </div>
  );
}

/** Tiny delta value chip */
function DeltaChip({ label, value }: { label: string; value: number }) {
  const isHigh = value > 2.0;
  return (
    <span
      className="text-[9px] font-mono px-1.5 py-0.5 rounded"
      style={{
        backgroundColor: isHigh
          ? "rgba(239, 68, 68, 0.1)"
          : "rgba(34, 197, 94, 0.1)",
        color: isHigh ? "#ef4444" : "#22c55e",
      }}
    >
      {label}: {value.toFixed(1)}°
    </span>
  );
}
