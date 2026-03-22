import { memo, useMemo } from "react";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatTimestamp } from "../utils/formatters";

function SystemCharts({ metricsHistory, systemStatus }) {
  const chartData = useMemo(
    () =>
      metricsHistory.map((point) => ({
        ...point,
        time: formatTimestamp(point.timestamp),
      })),
    [metricsHistory],
  );

  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <h2>Fleet Trends</h2>
          <p>Rolling last 50 batches for health and active anomaly pressure.</p>
        </div>
        <span className="panel__meta">{systemStatus?.topic || "vehicle.telemetry"}</span>
      </div>
      <div className="detail-chart">
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="healthFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#2563eb" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="anomalyFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f97316" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="time" hide />
            <YAxis />
            <Tooltip />
            <Area
              isAnimationActive={false}
              type="monotone"
              dataKey="averageHealth"
              stroke="#2563eb"
              fill="url(#healthFill)"
              strokeWidth={2}
            />
            <Area
              isAnimationActive={false}
              type="monotone"
              dataKey="anomalies"
              stroke="#f97316"
              fill="url(#anomalyFill)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export default memo(SystemCharts);
