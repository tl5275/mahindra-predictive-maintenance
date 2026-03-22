export function renderFleetOverview(fleetData) {
  const health = fleetData.fleet_health || {};
  const statuses = health.status_counts || {};

  return `
    <section class="kpi-grid">
      <article class="kpi-card">
        <div class="kpi-label">Fleet Size</div>
        <div class="kpi-value">${fleetData.fleet_size || 0}</div>
      </article>
      <article class="kpi-card">
        <div class="kpi-label">Avg Health Score</div>
        <div class="kpi-value">${(health.average_health_score || 0).toFixed(1)}</div>
      </article>
      <article class="kpi-card">
        <div class="kpi-label">Healthy / Warning</div>
        <div class="kpi-value">${statuses.healthy || 0} / ${statuses.warning || 0}</div>
      </article>
      <article class="kpi-card">
        <div class="kpi-label">Critical Vehicles</div>
        <div class="kpi-value">${statuses.critical || 0}</div>
      </article>
    </section>
  `;
}
