import { memo } from "react";

import { formatNumber, formatTimestamp, statusLabel } from "../utils/formatters";

function MetricPill({ label, value }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
      <span className="label-text" style={{ textTransform: "none" }}>{label}</span>
      <strong className="value-text">{value}</strong>
    </div>
  );
}

function insightCopy(details) {
  const latestAction = details?.latest?.recommended_action;
  if (latestAction) {
    return latestAction;
  }
  const alert = details?.alerts?.[0];
  if (alert?.recommended_action) {
    return alert.recommended_action;
  }
  const log = details?.maintenance_logs?.[0];
  if (log?.description) {
    return log.description;
  }
  return "Vehicle performance is being monitored for maintenance planning.";
}

function VehicleDetailPanel({ details, loading }) {
  if (!details?.latest) {
    return (
      <section className="panel panel--detail" style={{ border: 'none', padding: '32px' }}>
        <div className="skeleton-stack">
          <div className="skeleton-card">
            <div className="skeleton-line skeleton-line--title" />
            <div className="skeleton-line" />
            <div className="skeleton-line skeleton-line--short" />
          </div>
          <div className="skeleton-card">
            <div className="skeleton-line skeleton-line--title" />
            <div className="skeleton-line" />
          </div>
        </div>
      </section>
    );
  }

  const latest = details.latest;
  const healthScore = Math.max(0, Math.min(100, Number(latest.health || 0)));
  const insight = insightCopy(details);
  const nextServiceWindow = details?.maintenance_logs?.[0]?.scheduled_within_hours;

  return (
    <section className="panel panel--detail" style={{ border: 'none', padding: '32px' }}>
      <div style={{ marginBottom: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "32px", borderBottom: "1px solid #f0f0f0", paddingBottom: "16px" }}>
          <div style={{ display: "flex", gap: "12px", alignItems: "baseline" }}>
            <span style={{ fontSize: "16px", fontWeight: "400", letterSpacing: "0.5px" }}>{latest.vehicle_id}</span>
            <span style={{ color: "var(--muted)", fontSize: "14px" }}>{latest.model || "Mahindra Fleet"}</span>
          </div>
          <span style={{ color: `var(--${latest.status || "healthy"})`, fontSize: "13px", fontWeight: "600", textTransform: "uppercase", letterSpacing: "1px", display: "flex", alignItems: "center", gap: "6px" }}>
            <span className={`map-legend__dot map-legend__dot--${latest.status || "healthy"}`}></span>
            {statusLabel(latest.status)}
          </span>
        </div>
        
        <div style={{ marginBottom: "32px", display: "flex", flexDirection: "column", gap: "4px", alignItems: "center", textAlign: "center" }}>
          <div style={{ fontSize: "44px", fontWeight: "600", color: "#111", letterSpacing: "-0.5px", lineHeight: 1 }}>
            {formatNumber(latest.rul)} <span style={{ fontSize: "24px", color: "var(--muted)", fontWeight: "600", letterSpacing: "normal" }}>h</span>
          </div>
          <div className="sub-text">
            Remaining Useful Life
          </div>
        </div>

        <div style={{ width: "100%", height: "4px", background: "linear-gradient(to right, #16A34A, #F59E0B, #DC2626)", marginBottom: "32px", borderRadius: "2px", boxShadow: "0 0 12px rgba(245, 158, 11, 0.4)", opacity: 0.9 }} />
      </div>

      <div className="detail-grid" style={{ padding: 0, border: "none", marginTop: 0, gap: "20px" }}>
        <MetricPill label="RPM" value={formatNumber(latest.rpm)} />
        <MetricPill label="Temperature" value={`${formatNumber(latest.temp, 1)} C`} />
        <MetricPill label="Battery" value={`${formatNumber(latest.battery, 1)} %`} />
        <MetricPill label="Vibration" value={`${formatNumber(latest.vibration, 2)} g`} />
        <MetricPill label="Speed" value={`${formatNumber(latest.speed || 0)} km/h`} />
        <MetricPill label="Health Status" value={statusLabel(latest.status)} />
      </div>

      <div style={{ marginTop: "32px", borderTop: "1px solid #f0f0f0", paddingTop: "24px" }}>
        <div style={{ fontSize: "13px", color: "var(--muted)", marginBottom: "8px", fontWeight: "400" }}>Predictive Insights</div>
        <div style={{ fontSize: "15px", color: "var(--ink)", fontWeight: "400", lineHeight: 1.5 }}>{insight}</div>
      </div>
    </section>
  );
}

export default memo(VehicleDetailPanel);
