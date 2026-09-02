/**
 * StationDetail – Side panel for selected station
 * ==================================================
 * Shows the station's identity, current status, the three
 * temperature values with visual comparison bars, and key
 * delta metrics.
 */

import { Thermometer, MapPin, Clock, Hash } from "lucide-react";
import type { Station } from "../types";
import { DECISION_META } from "../types";

interface StationDetailProps {
  station: Station;
}

/** Small temperature pill with label + value */
function TempPill({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div
      className="flex flex-col items-center p-3 rounded-lg"
      style={{
        background: `linear-gradient(135deg, ${color}12, ${color}06)`,
        border: `1px solid ${color}30`,
      }}
    >
      <span className="text-[10px] uppercase tracking-wider mb-1" style={{ color: "#94a3b8" }}>
        {label}
      </span>
      <span className="text-lg font-bold" style={{ color }}>
        {value}°C
      </span>
    </div>
  );
}

export default function StationDetail({ station }: StationDetailProps) {
  const meta = DECISION_META[station.status];

  const diffAW = Math.abs(station.t_aws - station.t_witness).toFixed(2);
  const diffAP = Math.abs(station.t_aws - station.t_predicted).toFixed(2);
  const diffWP = Math.abs(station.t_witness - station.t_predicted).toFixed(2);

  return (
    <div className="glass-card p-4 animate-slide-up h-full flex flex-col gap-4 overflow-y-auto">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0 text-lg"
          style={{
            backgroundColor: meta.glow,
            color: meta.color,
          }}
        >
          {meta.icon}
        </div>
        <div className="min-w-0">
          <h3 className="text-sm font-bold text-[var(--text-primary)] truncate">
            {station.name}
          </h3>
          <div className="flex items-center gap-1.5 mt-1">
            <span className={`status-dot ${meta.dotClass}`} />
            <span
              className="text-xs font-semibold"
              style={{ color: meta.color }}
            >
              {meta.label}
            </span>
          </div>
        </div>
      </div>

      {/* Station metadata */}
      <div className="grid grid-cols-2 gap-2 text-[11px]">
        <div className="flex items-center gap-1.5 text-[var(--text-secondary)]">
          <Hash size={12} className="text-[var(--text-muted)]" />
          {station.id}
        </div>
        <div className="flex items-center gap-1.5 text-[var(--text-secondary)]">
          <MapPin size={12} className="text-[var(--text-muted)]" />
          {station.lat.toFixed(2)}°N, {station.lng.toFixed(2)}°E
        </div>
        <div className="flex items-center gap-1.5 text-[var(--text-secondary)]">
          <Clock size={12} className="text-[var(--text-muted)]" />
          {new Date(station.lastSeen).toLocaleTimeString("en-IN", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
        <div className="flex items-center gap-1.5 text-[var(--text-secondary)]">
          <Thermometer size={12} className="text-[var(--text-muted)]" />
          {station.totalReadings} readings
        </div>
      </div>

      {/* Separator */}
      <div className="h-px bg-[var(--border-subtle)]" />

      {/* Three temperature values */}
      <div>
        <h4 className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] mb-2">
          Temperature Comparison
        </h4>
        <div className="grid grid-cols-3 gap-2">
          <TempPill label="AWS" value={station.t_aws} color="#f59e0b" />
          <TempPill label="Witness" value={station.t_witness} color="#22c55e" />
          <TempPill label="Predicted" value={station.t_predicted} color="#a855f7" />
        </div>
      </div>

      {/* Separator */}
      <div className="h-px bg-[var(--border-subtle)]" />

      {/* Delta metrics */}
      <div>
        <h4 className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] mb-2">
          Divergence Metrics
        </h4>
        <div className="space-y-2">
          <DeltaRow
            label="|AWS − Witness|"
            value={diffAW}
            threshold={2.0}
            exceeded={parseFloat(diffAW) > 2.0}
          />
          <DeltaRow
            label="|AWS − Predicted|"
            value={diffAP}
            threshold={2.0}
            exceeded={parseFloat(diffAP) > 2.0}
          />
          <DeltaRow
            label="|Witness − Pred|"
            value={diffWP}
            threshold={1.5}
            exceeded={parseFloat(diffWP) > 1.5}
          />
        </div>
      </div>
    </div>
  );
}

/** Single delta metric row with visual bar */
function DeltaRow({
  label,
  value,
  threshold,
  exceeded,
}: {
  label: string;
  value: string;
  threshold: number;
  exceeded: boolean;
}) {
  const pct = Math.min((parseFloat(value) / (threshold * 3)) * 100, 100);
  const barColor = exceeded ? "#ef4444" : "#22c55e";

  return (
    <div>
      <div className="flex justify-between items-center text-[11px] mb-1">
        <span className="text-[var(--text-secondary)]">{label}</span>
        <span
          className="font-mono font-semibold"
          style={{ color: exceeded ? "#ef4444" : "#22c55e" }}
        >
          {value}°C
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-[var(--border-subtle)] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${pct}%`,
            backgroundColor: barColor,
            boxShadow: `0 0 8px ${barColor}60`,
          }}
        />
      </div>
    </div>
  );
}
