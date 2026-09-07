/**
 * MapView – Live GIS Map of Indian Weather Stations
 * ====================================================
 * Renders a Leaflet map centred on India with color-coded
 * circle markers for each station.  Clicking a marker selects
 * the station and opens the detail panel.
 */

import { useEffect, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  useMap,
} from "react-leaflet";
import type { Station } from "../types";
import { DECISION_META } from "../types";

interface MapViewProps {
  stations: Station[];
  selectedStation: Station | null;
  onSelectStation: (station: Station) => void;
}

/** Fly to a selected station smoothly */
function FlyToStation({ station }: { station: Station | null }) {
  const map = useMap();
  useEffect(() => {
    if (station) {
      map.flyTo([station.lat, station.lng], 7, { duration: 1.2 });
    }
  }, [station, map]);
  return null;
}

export default function MapView({
  stations,
  selectedStation,
  onSelectStation,
}: MapViewProps) {
  const mapRef = useRef(null);

  return (
    <div className="w-full h-full rounded-xl overflow-hidden border border-[var(--border-subtle)]">
      <MapContainer
        center={[22.5, 79.0]}
        zoom={5}
        className="w-full h-full"
        zoomControl={true}
        ref={mapRef}
        attributionControl={true}
      >
        {/* Dark-themed map tiles (Esri World Dark Gray Canvas – free, no API key) */}
<TileLayer
  attribution='&copy; <a href="https://www.esri.com/">Esri</a> &mdash; Esri, HERE, Garmin, FAO, NOAA, USGS'
  url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
/>

        <FlyToStation station={selectedStation} />

        {/* Station markers */}
        {stations.map((station) => {
          const meta = DECISION_META[station.status];
          const isSelected = selectedStation?.id === station.id;

          return (
            <CircleMarker
              key={station.id}
              center={[station.lat, station.lng]}
              radius={isSelected ? 14 : 9}
              pathOptions={{
                color: meta.color,
                fillColor: meta.color,
                fillOpacity: isSelected ? 0.9 : 0.65,
                weight: isSelected ? 3 : 2,
                opacity: 1,
              }}
              eventHandlers={{
                click: () => onSelectStation(station),
              }}
            >
              <Popup>
                <div style={{ minWidth: 180 }}>
                  <p
                    style={{
                      fontWeight: 700,
                      fontSize: 13,
                      marginBottom: 6,
                      color: "#f1f5f9",
                    }}
                  >
                    {station.name}
                  </p>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      marginBottom: 8,
                    }}
                  >
                    <span
                      className="status-dot"
                      style={{ backgroundColor: meta.color }}
                    />
                    <span style={{ color: meta.color, fontSize: 12, fontWeight: 600 }}>
                      {meta.label}
                    </span>
                  </div>
                  {/* Temperature values grid */}
                  {(() => {
                    const isImputed = station.is_imputed || station.status === "PRIMARY_DRIFT";
                    const tImp = station.t_imputed ?? (station.t_witness != null && station.t_predicted != null ? Number(((0.6 * station.t_witness) + (0.4 * station.t_predicted)).toFixed(1)) : null);
                    const origAws = station.original_t_aws ?? station.t_aws;

                    return (
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: isImputed ? "1fr 1fr 1fr 1fr" : "1fr 1fr 1fr",
                          gap: 4,
                          fontSize: 11,
                        }}
                      >
                        <div>
                          <span style={{ color: "#94a3b8" }}>{isImputed ? "AWS (Orig)" : "AWS"}</span>
                          <br />
                          <span style={{ color: "#f59e0b", fontWeight: 600, textDecoration: isImputed ? "line-through" : "none" }}>
                            {origAws != null ? `${origAws}°C` : "—"}
                          </span>
                        </div>
                        {isImputed && (
                          <div>
                            <span style={{ color: "#34d399", fontWeight: 700 }}>Imputed</span>
                            <br />
                            <span style={{ color: "#34d399", fontWeight: 700 }}>
                              {tImp != null ? `${tImp}°C` : "—"}
                            </span>
                          </div>
                        )}
                        <div>
                          <span style={{ color: "#94a3b8" }}>Witness</span>
                          <br />
                          <span style={{ color: "#22c55e", fontWeight: 600 }}>
                            {station.t_witness != null ? `${station.t_witness}°C` : "—"}
                          </span>
                        </div>
                        <div>
                          <span style={{ color: "#94a3b8" }}>Predicted</span>
                          <br />
                          <span style={{ color: "#a855f7", fontWeight: 600 }}>
                            {station.t_predicted != null ? `${station.t_predicted}°C` : "—"}
                          </span>
                        </div>
                      </div>
                    );
                  })()}
                  {station.neighbours_used != null && (
                    <div
                      style={{
                        marginTop: 6,
                        display: "flex",
                        alignItems: "center",
                        gap: 5,
                        fontSize: 10,
                        color: "#c084fc",
                        background: "rgba(168, 85, 247, 0.12)",
                        padding: "3px 6px",
                        borderRadius: 6,
                        border: "1px solid rgba(168, 85, 247, 0.25)",
                      }}
                    >
                      <span>🌐</span>
                      <span>
                        Predicted using {station.neighbours_used} neighbouring station{station.neighbours_used === 1 ? "" : "s"}
                      </span>
                    </div>
                  )}
                  <p
                    style={{
                      color: "#64748b",
                      fontSize: 10,
                      marginTop: 8,
                      borderTop: "1px solid #1e293b",
                      paddingTop: 6,
                    }}
                  >
                    {station.id}
                    {station.lastUpdated
                      ? ` · ${new Date(station.lastUpdated).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}`
                      : " · awaiting data"}
                  </p>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
