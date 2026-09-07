/**
 * Dashboard – Main Command Center Page
 * =======================================
 * Assembles all sub-components into a single operations-center
 * layout with:
 *   • Top bar  – branding + live indicator + live clock
 *   • Row 1    – Status summary cards
 *   • Row 2    – Map (left) + Detail/Chart + Tickets (right)
 *
 * Polls GET /api/stations/status every 5s for live updates.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Radar, Satellite, Wifi } from "lucide-react";
import type { Station } from "../types";
import { fetchStations } from "../services/api";

import StatusCards from "../components/StatusCards";
import MapView from "../components/MapView";
import StationDetail from "../components/StationDetail";
import StationChart from "../components/StationChart";
import TicketPanel from "../components/TicketPanel";

/** Polling interval in milliseconds */
const POLL_INTERVAL = 5_000;

export default function Dashboard() {
  const [stations, setStations] = useState<Station[]>([]);
  const [selected, setSelected] = useState<Station | null>(null);
  const [clock, setClock] = useState(new Date());
  const [isLive, setIsLive] = useState(false);

  // Ref to keep the selected station id stable across polls
  const selectedIdRef = useRef<string | null>(null);

  /** Fetch stations and update state, preserving selection */
  const loadStations = useCallback(async () => {
    const { data, live } = await fetchStations();
    setStations(data);
    setIsLive(live);

    // Update the selected station object with fresh data
    if (selectedIdRef.current) {
      const updated = data.find((s) => s.id === selectedIdRef.current);
      if (updated) setSelected(updated);
    }
  }, []);

  /* Fetch on mount + poll every 5s */
  useEffect(() => {
    // Initial fetch
    loadStations().then(() => {
      // Auto-select first non-normal station for immediate visual impact
      setStations((prev) => {
        const interesting = prev.find((s) => s.status !== "NORMAL");
        if (interesting && !selectedIdRef.current) {
          selectedIdRef.current = interesting.id;
          setSelected(interesting);
        }
        return prev;
      });
    });

    // Polling interval
    const id = setInterval(loadStations, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [loadStations]);

  /* Live clock */
  useEffect(() => {
    const id = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const handleSelectStation = useCallback((station: Station) => {
    selectedIdRef.current = station.id;
    setSelected(station);
  }, []);

  const handleSelectStationById = useCallback((stationId: string) => {
    const target = stations.find((s) => s.id === stationId);
    if (target) {
      handleSelectStation(target);
    }
  }, [stations, handleSelectStation]);

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-[var(--bg-primary)]">
      {/* ═══ Top Bar ═══ */}
      <header className="flex items-center justify-between px-5 py-3 border-b border-[var(--border-subtle)] shrink-0">
        {/* Left – Branding */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Satellite size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-[var(--text-primary)] leading-none">
              The Witness Network
            </h1>
            <p className="text-[10px] text-[var(--text-muted)] mt-0.5 tracking-wide uppercase">
              Weather Anomaly Command Center
            </p>
          </div>
        </div>

        {/* Center – Status indicator */}
        <div className="flex items-center gap-4">
          {/* Live / Demo indicator */}
          <div className="flex items-center gap-1.5 text-[11px]">
            <span
              className={`w-2 h-2 rounded-full ${
                isLive
                  ? "bg-[var(--accent-green)] pulse-live"
                  : "bg-amber-500 animate-pulse"
              }`}
            />
            <span
              className={`font-semibold ${
                isLive
                  ? "text-[var(--accent-green)]"
                  : "text-amber-500"
              }`}
            >
              {isLive ? "Live" : "Demo"}
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-[var(--text-secondary)]">
            <Wifi size={12} className={isLive ? "text-[var(--accent-green)]" : "text-amber-500"} />
            <span>{stations.length} Nodes</span>
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-[var(--text-secondary)]">
            <Radar size={12} className="text-[var(--accent-cyan)]" />
            <span>ε=2.0 δ=1.5</span>
          </div>
        </div>

        {/* Right – Clock */}
        <div className="text-right">
          <p className="text-sm font-mono font-bold text-[var(--text-primary)] tracking-wide">
            {clock.toLocaleTimeString("en-IN", {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
              hour12: false,
            })}
          </p>
          <p className="text-[10px] text-[var(--text-muted)] font-mono">
            {clock.toLocaleDateString("en-IN", {
              day: "2-digit",
              month: "short",
              year: "numeric",
            })}{" "}
            IST
          </p>
        </div>
      </header>

      {/* ═══ Main Content ═══ */}
      <main className="flex-1 flex flex-col gap-3 p-4 overflow-hidden">
        {/* Row 1 – Status Cards */}
        <StatusCards stations={stations} />

        {/* Row 2 – Map + Sidebar */}
        <div className="flex-1 flex gap-3 min-h-0">
          {/* Left – Map (takes ~65% width) */}
          <div className="flex-[2] min-w-0">
            <MapView
              stations={stations}
              selectedStation={selected}
              onSelectStation={handleSelectStation}
            />
          </div>

          {/* Right sidebar (takes ~35% width) */}
          <div className="flex-[1] flex flex-col gap-3 min-w-[340px] max-w-[420px]">
            {selected ? (
              <>
                {/* Station detail card */}
                <div className="shrink-0">
                  <StationDetail station={selected} />
                </div>

                {/* Temperature chart */}
                <div className="shrink-0">
                  <StationChart station={selected} />
                </div>

                {/* Tickets panel fills remaining height */}
                <div className="flex-1 min-h-0">
                  <TicketPanel
                    onSelectStation={handleSelectStationById}
                    selectedStationId={selected?.id ?? null}
                  />
                </div>
              </>
            ) : (
              <>
                {/* No station selected – show full tickets panel */}
                <div className="glass-card p-6 flex flex-col items-center justify-center gap-3 shrink-0">
                  <div className="w-12 h-12 rounded-full bg-[var(--accent-cyan)]/10 flex items-center justify-center">
                    <Radar size={24} className="text-[var(--accent-cyan)]" />
                  </div>
                  <p className="text-sm text-[var(--text-secondary)] text-center">
                    Select a station on the map
                    <br />
                    <span className="text-[var(--text-muted)] text-xs">
                      to view details and temperature trends
                    </span>
                  </p>
                </div>

                <div className="flex-1 min-h-0">
                  <TicketPanel
                    onSelectStation={handleSelectStationById}
                    selectedStationId={selected?.id ?? null}
                  />
                </div>
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
