import { memo } from "react";

import { formatNumber, formatTimestamp, statusLabel } from "../utils/formatters";

function AlertPanel({ alerts = [] }) {
  return (
    <section className="panel">
      <div className="panel__header" style={{ marginBottom: "16px" }}>
        <div>
          <h2 className="label-text">Maintenance Alerts</h2>
        </div>
        <span className="sub-text">{alerts.length > 0 ? `${alerts.length} active` : "No active alerts"}</span>
      </div>
      <div className="alert-list">
        {alerts.length > 0 ? (
          alerts.slice(0, 5).map((alert) => (
            <article 
              className={`alert-row alert-row--${alert.status}`}
              key={alert.vehicle_id} 
              style={{
                display: "flex", 
                flexDirection: "column", 
                gap: "4px", 
                padding: "12px 16px", 
                borderBottom: "none",
                borderTop: "none",
                borderRight: "none",
                borderLeft: `4px solid var(--${alert.status === "critical" ? "critical" : "warning"})`,
                borderRadius: "4px",
                marginBottom: "8px"
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: "2px", marginBottom: "4px" }}>
                <strong style={{ fontSize: "14px", fontWeight: "600", color: "var(--ink)", letterSpacing: "0.2px" }}>{alert.vehicle_id}</strong>
                <span style={{ fontSize: "14px", color: "var(--ink)", fontWeight: "400" }}>{alert.issue}</span>
              </div>
              
              <div className="sub-text" style={{ display: "flex", alignItems: "center" }}>
                Health {formatNumber(alert.health, 0)}% 
                <span style={{ color: "rgba(0,0,0,0.1)", margin: "0 8px" }}>|</span> 
                RUL {formatNumber(alert.rul)}h
              </div>
            </article>
          ))
        ) : (
          <div className="empty-state">
            <strong>No active maintenance alerts.</strong>
            <span>Vehicles with warning or critical status will appear here automatically.</span>
          </div>
        )}
      </div>
    </section>
  );
}

export default memo(AlertPanel);
