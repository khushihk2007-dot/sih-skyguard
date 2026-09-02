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

export default function TicketPanel() {
  const [tickets, setTickets] = useState<AnomalyTicket[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTickets(15).then((data) => {
      setTickets(data);
      setLoading(false);
    });
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
            <TicketRow key={ticket.id} ticket={ticket} index={i} timeAgo={timeAgo} />
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
}: {
  ticket: AnomalyTicket;
  index: number;
  timeAgo: (iso: string) => string;
}) {
  const meta = DECISION_META[ticket.decision];
  const sevColor = SEVERITY_COLORS[ticket.severity];

  return (
    <div
      className="p-3 rounded-lg transition-all duration-200 cursor-pointer animate-fade-in"
      style={{
        background: `linear-gradient(135deg, ${meta.color}08, transparent)`,
        border: `1px solid ${meta.color}15`,
        animationDelay: `${index * 40}ms`,
        animationFillMode: "backwards",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = `linear-gradient(135deg, ${meta.color}15, transparent)`;
        e.currentTarget.style.borderColor = `${meta.color}30`;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = `linear-gradient(135deg, ${meta.color}08, transparent)`;
        e.currentTarget.style.borderColor = `${meta.color}15`;
      }}
    >
      {/* Top row: decision + severity + time */}
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
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
        </div>
        <div className="flex items-center gap-1 text-[10px] text-[var(--text-muted)]">
          <Clock size={10} />
          {timeAgo(ticket.detected_at)}
        </div>
      </div>

      {/* Station ID */}
      <p className="text-[11px] font-mono text-[var(--text-secondary)] mb-1">
        {ticket.station_id}
      </p>

      {/* Reason (truncated) */}
      <p className="text-[10px] text-[var(--text-muted)] leading-relaxed line-clamp-2">
        {ticket.reason}
      </p>

      {/* Delta chips */}
      <div className="flex gap-2 mt-2">
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
