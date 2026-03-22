export function renderAnalyticsPanel(failureAnalytics) {
  if (!failureAnalytics) {
    return `<p class="small">Analytics unavailable.</p>`;
  }

  const forecast = failureAnalytics.forecast || {};
  const manufacturingFeedback = failureAnalytics.manufacturing_feedback || [];

  return `
    <div class="stat-row"><span>Service Utilization</span><strong>${forecast.service_utilization_percent || 0}%</strong></div>
    <div class="stat-row"><span>Jobs Next 24h</span><strong>${forecast.predicted_jobs_next_24h || 0}</strong></div>
    <div class="stat-row"><span>Jobs Next 7d</span><strong>${forecast.predicted_jobs_next_7d || 0}</strong></div>
    <h3 style="font-size: 0.92rem; margin: 12px 0 6px">Manufacturing Feedback</h3>
    <ul class="list">
      ${
        manufacturingFeedback.length
          ? manufacturingFeedback
              .slice(0, 4)
              .map((item) => `<li>${item.model}: ${item.issue} (${item.occurrences})</li>`)
              .join("")
          : "<li>No recurring issue clusters yet.</li>"
      }
    </ul>
  `;
}
