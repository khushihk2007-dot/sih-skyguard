/**
 * StationDetail – Side panel for selected station
 * ==================================================
 * Shows the station's identity, current status, the three
 * temperature values with visual comparison bars, and key
 * delta metrics.  All data comes from the live Station object
 * returned by GET /api/stations/status.
 */

import { MapPin, Clock, Hash, Sparkles, HelpCircle } from "lucide-react";
import type { Station } from "../types";
import { DECISION_META, SEVERITY_COLORS } from "../types";

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
  value: number | null;
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
        {value != null ? `${value.toFixed(1)}°C` : "—"}
      </span>
    </div>
  );
}

export default function StationDetail({ station }: StationDetailProps) {
  const meta = DECISION_META[station.status] ?? DECISION_META.NORMAL;
  const sevColor = SEVERITY_COLORS[station.severity] ?? SEVERITY_COLORS.LOW;

  const statusUpper = String(station.status ?? "").toUpperCase();
  const isImputed = Boolean(station.is_imputed) || statusUpper === "PRIMARY_DRIFT";

  const tAws = station.t_aws ?? 0;
  const tWit = station.t_witness ?? 0;
  const tPred = station.t_predicted ?? 0;
  const hasTemps = station.t_aws != null && station.t_witness != null && station.t_predicted != null;

  const computedImputed = station.t_imputed ?? (station.t_witness != null && station.t_predicted != null ? Number(((0.6 * station.t_witness) + (0.4 * station.t_predicted)).toFixed(1)) : null);
  const origAws = station.original_t_aws ?? station.t_aws;

  const diffAW = Math.abs(tAws - tWit).toFixed(2);
  const diffAP = Math.abs(tAws - tPred).toFixed(2);
  const diffWP = Math.abs(tWit - tPred).toFixed(2);

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
            {/* Severity badge */}
            <span
              className="text-[9px] px-1.5 py-0.5 rounded font-semibold uppercase ml-1"
              style={{
                backgroundColor: `${sevColor}18`,
                color: sevColor,
              }}
            >
              {station.severity}
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
        <div className="flex items-center gap-1.5 text-[var(--text-secondary)] col-span-2">
          <Clock size={12} className="text-[var(--text-muted)]" />
          {station.lastUpdated
            ? new Date(station.lastUpdated).toLocaleTimeString("en-IN", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })
            : "No data yet"}
        </div>
      </div>

      {/* Dedicated Root Cause Section */}
      <div
        className="p-3.5 rounded-xl border animate-fade-in flex flex-col gap-2 relative overflow-hidden"
        style={{
          background: `linear-gradient(135deg, ${meta.color}14, rgba(15, 23, 42, 0.7))`,
          borderColor: `${meta.color}35`,
          boxShadow: `0 0 15px ${meta.color}0D`,
        }}
      >
        {/* Card Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <HelpCircle size={14} style={{ color: meta.color }} />
            <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">
              Why This Decision?
            </span>
          </div>
          <span
            className="text-[9px] px-2 py-0.5 rounded font-bold uppercase tracking-wider"
            style={{
              backgroundColor: `${meta.color}20`,
              color: meta.color,
              border: `1px solid ${meta.color}40`,
            }}
          >
            {meta.label}
          </span>
        </div>

        {/* 1-Line Judge-Friendly Summary */}
        <div className="text-xs font-bold text-[var(--text-primary)] flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: meta.color }} />
          <span>{meta.summary}</span>
        </div>

        {/* Detailed Reason Box */}
        <div className="text-[11px] text-[var(--text-secondary)] leading-relaxed bg-[var(--bg-primary)]/50 p-2.5 rounded-lg border border-white/5 font-mono">
          {station.reason || "All sensor metrics remain within nominal threshold limits."}
        </div>

        {/* Mention Imputation for PRIMARY_DRIFT when active */}
        {isImputed && (
          <div className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-medium bg-emerald-500/10 p-2 rounded-lg border border-emerald-500/25">
            <Sparkles size={13} className="shrink-0 animate-pulse text-emerald-400" />
            <span>
              <strong>Imputation Active:</strong> Corrected reading of{" "}
              <strong className="text-emerald-300 font-bold">
                {computedImputed != null ? `${computedImputed.toFixed(1)}°C` : "—"}
              </strong>{" "}
              generated to replace drifted AWS value ({origAws != null ? `${origAws.toFixed(1)}°C` : "—"}).
            </span>
          </div>
        )}
      </div>

      {/* Imputation Comparison Section (Only when isImputed is true) */}
      {isImputed && (
        <div
          className="p-3.5 rounded-xl border animate-fade-in flex flex-col gap-2.5"
          style={{
            background: "linear-gradient(135deg, rgba(34, 197, 94, 0.08), rgba(245, 158, 11, 0.05))",
            borderColor: "rgba(34, 197, 94, 0.3)",
            boxShadow: "0 0 15px rgba(34, 197, 94, 0.08)",
          }}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Sparkles size={14} className="text-emerald-400 animate-pulse" />
              <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-400">
                Imputed Temperature
              </span>
            </div>
            <span className="text-[9px] px-2 py-0.5 rounded font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              CORRECTED
            </span>
          </div>

          <p className="text-[10px] text-[var(--text-secondary)] leading-relaxed">
            AWS sensor drift detected. Temperature corrected using 60% Witness + 40% Predicted weights.
          </p>

          <div className="grid grid-cols-2 gap-2 mt-0.5">
            {/* Original AWS (Drifted) */}
            <div className="flex flex-col p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/25">
              <div className="flex items-center justify-between text-[10px] text-amber-400 font-semibold mb-1">
                <span>Original AWS</span>
                <span className="text-[9px] bg-amber-500/20 px-1 py-0.5 rounded text-amber-300">Drifted</span>
              </div>
              <span className="text-base font-bold text-amber-400 line-through opacity-80">
                {origAws != null ? `${origAws.toFixed(1)}°C` : "—"}
              </span>
            </div>

            {/* Imputed Value (Corrected) */}
            <div className="flex flex-col p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
              <div className="flex items-center justify-between text-[10px] text-emerald-400 font-semibold mb-1">
                <span>Imputed Value</span>
                <span className="text-[9px] bg-emerald-500/20 px-1 py-0.5 rounded text-emerald-300">Corrected</span>
              </div>
              <span className="text-base font-bold text-emerald-400">
                {computedImputed != null ? `${computedImputed.toFixed(1)}°C` : "—"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Separator */}
      <div className="h-px bg-[var(--border-subtle)]" />

      {/* Temperature values */}
      <div>
        <h4 className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] mb-2">
          Temperature Comparison
        </h4>
        <div className={`grid gap-2 ${isImputed ? "grid-cols-4" : "grid-cols-3"}`}>
          <TempPill label={isImputed ? "AWS (Orig)" : "AWS"} value={origAws} color="#f59e0b" />
          {isImputed && (
            <TempPill label="Imputed" value={computedImputed} color="#10b981" />
          )}
          <TempPill label="Witness" value={station.t_witness} color="#22c55e" />
          <TempPill label="Predicted" value={station.t_predicted} color="#a855f7" />
        </div>
      </div>

      {/* Separator */}
      <div className="h-px bg-[var(--border-subtle)]" />

      {/* Delta metrics (only when we have temperature data) */}
      {hasTemps && (
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
      )}
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
