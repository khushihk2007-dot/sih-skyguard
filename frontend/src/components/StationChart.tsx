/**
 * StationChart – Real-time temperature comparison chart
 * =======================================================
 * Recharts line chart that plots T_AWS, T_Witness, and
 * T_Predicted over the last 24 hours for a selected station.
 */

import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { TrendingUp } from "lucide-react";
import type { ChartDataPoint, Station } from "../types";
import { fetchStationChart } from "../services/api";

interface StationChartProps {
  station: Station;
}

export default function StationChart({ station }: StationChartProps) {
  const [data, setData] = useState<ChartDataPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    fetchStationChart(station.id).then((chartData) => {
      if (!cancelled) {
        setData(chartData);
        setLoading(false);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [station.id]);

  return (
    <div className="glass-card p-4 animate-slide-up" style={{ animationDelay: "100ms" }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <TrendingUp size={14} className="text-[var(--accent-cyan)]" />
          <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--text-secondary)]">
            24h Temperature Trend
          </h4>
        </div>
        <span className="text-[10px] text-[var(--text-muted)] font-mono">
          {station.id}
        </span>
      </div>

      {/* Chart */}
      {loading ? (
        <div className="h-[200px] flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-[var(--accent-cyan)] border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart
            data={data}
            margin={{ top: 5, right: 10, left: -10, bottom: 0 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--border-subtle)"
              vertical={false}
            />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 10, fill: "#64748b" }}
              axisLine={{ stroke: "#1e293b" }}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 10, fill: "#64748b" }}
              axisLine={false}
              tickLine={false}
              domain={["auto", "auto"]}
              tickFormatter={(v: number) => `${v}°`}
            />
            <Tooltip
              contentStyle={{
                background: "#1a2035",
                border: "1px solid #1e293b",
                borderRadius: 8,
                fontSize: 11,
                boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
              }}
              labelStyle={{ color: "#94a3b8", marginBottom: 4 }}
              itemStyle={{ padding: 0 }}
              formatter={(value: number) => [`${value}°C`]}
            />
            <Legend
              verticalAlign="top"
              height={28}
              iconType="circle"
              iconSize={8}
              formatter={(value: string) => (
                <span style={{ color: "#94a3b8", fontSize: 11 }}>{value}</span>
              )}
            />
            <Line
              type="monotone"
              dataKey="t_aws"
              name="AWS"
              stroke="#f59e0b"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: "#f59e0b" }}
            />
            <Line
              type="monotone"
              dataKey="t_witness"
              name="Witness"
              stroke="#22c55e"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: "#22c55e" }}
            />
            <Line
              type="monotone"
              dataKey="t_predicted"
              name="Predicted"
              stroke="#a855f7"
              strokeWidth={2}
              strokeDasharray="5 3"
              dot={false}
              activeDot={{ r: 4, fill: "#a855f7" }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
