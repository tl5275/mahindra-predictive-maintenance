import { memo } from "react";

import { formatNumber, formatTimestamp } from "../utils/formatters";

function MetricCard({ label, value, tone = "default", detail }) {
  return (
    <article className={`metric-card metric-card--${tone}`}>
      <span className="metric-card__label">{label}</span>
      <strong className="metric-card__value">{value}</strong>
      <span className="metric-card__detail">{detail}</span>
    </article>
  );
}

function MetricStrip({
  fleetSize,
  wsConnected,
  alertCount,
  averageHealth,
  criticalCount,
  systemStatus,
}) {
  return (
    <section className="metric-strip">
      <MetricCard
        label="Monitored Vehicles"
        value={formatNumber(fleetSize)}
        detail="Active fleet coverage across the operating network"
      />
      <MetricCard
        label="Fleet Health Overview"
        value={`${formatNumber(averageHealth, 1)}%`}
        tone={averageHealth < 70 ? "warning" : "default"}
        detail={`${formatNumber(criticalCount)} vehicles need priority review`}
      />
      <MetricCard
        label="Live Data Stream"
        value={wsConnected ? "Connected" : "Syncing"}
        tone={wsConnected ? "healthy" : "warning"}
        detail={`Last refresh ${formatTimestamp(systemStatus?.last_processed_at)}`}
      />
      <MetricCard
        label="Predictive Insights"
        value={formatNumber(alertCount)}
        tone={alertCount > 0 ? "critical" : "healthy"}
        detail="Maintenance alerts requiring operational attention"
      />
    </section>
  );
}

export default memo(MetricStrip);
