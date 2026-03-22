export function renderAlertsPanel(failureAnalytics) {
  if (!failureAnalytics) {
    return `<h2>Alerts</h2><p class="small">No alerts yet.</p>`;
  }

  const failureEntries = Object.entries(failureAnalytics.failure_summary || {});
  const topFailures = failureEntries
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([issue, count]) => `<li>${issue}: <strong>${count}</strong></li>`)
    .join("");

  const forecast = failureAnalytics.forecast || {};
  return `
    <h2>Active Alerts</h2>
    <div class="stat-row"><span>Diagnoses</span><strong>${failureAnalytics.diagnoses_count || 0}</strong></div>
    <div class="stat-row"><span>Anomalies</span><strong>${failureAnalytics.anomalies_count || 0}</strong></div>
    <div class="stat-row"><span>Jobs Next 24h</span><strong>${forecast.predicted_jobs_next_24h || 0}</strong></div>
    <div class="stat-row"><span>Jobs Next 7d</span><strong>${forecast.predicted_jobs_next_7d || 0}</strong></div>
    <h3 style="font-size: 0.92rem; margin: 12px 0 6px">Top Failures</h3>
    <ul class="list">${topFailures || "<li>None detected</li>"}</ul>
  `;
}
