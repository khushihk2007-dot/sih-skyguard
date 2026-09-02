/**
 * StatusCards – Summary overview tiles
 * ======================================
 * Displays total station count and breakdown by anomaly decision.
 * Each card has a color-coded glow, icon, and animated count.
 */

import { useMemo } from "react";
import {
  Radio,
  AlertTriangle,
  XOctagon,
  Zap,
  Activity,
} from "lucide-react";
import type { Station } from "../types";
import { DECISION_META } from "../types";

interface StatusCardsProps {
  stations: Station[];
}

interface CardDef {
  label: string;
  count: number;
  color: string;
  glow: string;
  icon: React.ReactNode;
}

export default function StatusCards({ stations }: StatusCardsProps) {
  const cards: CardDef[] = useMemo(() => {
    const counts = {
      NORMAL: 0,
      PRIMARY_DRIFT: 0,
      WITNESS_FAULT: 0,
      TRUE_EXTREME: 0,
    };
    stations.forEach((s) => {
      if (s.status in counts) counts[s.status]++;
    });

    return [
      {
        label: "Total Stations",
        count: stations.length,
        color: "#06b6d4",
        glow: "rgba(6, 182, 212, 0.12)",
        icon: <Radio size={20} />,
      },
      {
        label: "Normal",
        count: counts.NORMAL,
        color: DECISION_META.NORMAL.color,
        glow: DECISION_META.NORMAL.glow,
        icon: <Activity size={20} />,
      },
      {
        label: "Primary Drift",
        count: counts.PRIMARY_DRIFT,
        color: DECISION_META.PRIMARY_DRIFT.color,
        glow: DECISION_META.PRIMARY_DRIFT.glow,
        icon: <AlertTriangle size={20} />,
      },
      {
        label: "Witness Fault",
        count: counts.WITNESS_FAULT,
        color: DECISION_META.WITNESS_FAULT.color,
        glow: DECISION_META.WITNESS_FAULT.glow,
        icon: <XOctagon size={20} />,
      },
      {
        label: "True Extreme",
        count: counts.TRUE_EXTREME,
        color: DECISION_META.TRUE_EXTREME.color,
        glow: DECISION_META.TRUE_EXTREME.glow,
        icon: <Zap size={20} />,
      },
    ];
  }, [stations]);

  return (
    <div className="grid grid-cols-5 gap-3">
      {cards.map((card, i) => (
        <div
          key={card.label}
          className="glass-card p-4 animate-slide-up flex items-center gap-3"
          style={{
            animationDelay: `${i * 60}ms`,
            animationFillMode: "backwards",
            boxShadow: `0 0 20px ${card.glow}`,
          }}
        >
          {/* Icon */}
          <div
            className="flex items-center justify-center w-10 h-10 rounded-lg shrink-0"
            style={{
              backgroundColor: card.glow,
              color: card.color,
            }}
          >
            {card.icon}
          </div>

          {/* Text */}
          <div className="min-w-0">
            <p
              className="text-2xl font-bold tracking-tight leading-none"
              style={{ color: card.color }}
            >
              {card.count}
            </p>
            <p className="text-xs mt-0.5 truncate" style={{ color: "#94a3b8" }}>
              {card.label}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
