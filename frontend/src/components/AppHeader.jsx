import { memo } from "react";

function MahindraMark() {
  return (
    <svg
      aria-label="Mahindra logo"
      className="brand-mark"
      viewBox="0 0 64 64"
      role="img"
    >
      <path
        d="M14 46V18l18 16 18-16v28"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="7"
      />
    </svg>
  );
}

function HeaderBadge({ healthy = true, label }) {
  return (
    <span className={`header-badge ${healthy ? "header-badge--healthy" : "header-badge--warning"}`}>
      <i className="header-badge__dot" />
      {label}
    </span>
  );
}

function AppHeader({ wsConnected, systemHealthy }) {
  return (
    <header className="app-header">
      <div className="app-header__brand">
        <MahindraMark />
        <div className="app-header__copy">
          <h1>Mahindra Predictive Maintenance Platform</h1>
          <p>Intelligent Fleet Health Monitoring &amp; Predictive Maintenance</p>
        </div>
      </div>

      <div className="app-header__status">
        <HeaderBadge healthy={wsConnected} label="Live Data" />
        <HeaderBadge healthy={systemHealthy} label="System Healthy" />
      </div>
    </header>
  );
}

export default memo(AppHeader);
