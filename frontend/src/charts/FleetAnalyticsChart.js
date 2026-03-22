export function drawFleetAnalyticsChart(canvas, healthData, failureData) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#f8fbfe";
  ctx.fillRect(0, 0, width, height);

  const statusCounts = healthData?.status_counts || { healthy: 0, warning: 0, critical: 0 };
  const bars = [
    { label: "Healthy", value: statusCounts.healthy || 0, color: "#1d8148" },
    { label: "Warning", value: statusCounts.warning || 0, color: "#cc8b00" },
    { label: "Critical", value: statusCounts.critical || 0, color: "#c84630" },
  ];
  const maxValue = Math.max(1, ...bars.map((item) => item.value));

  const barWidth = 70;
  const gap = 38;
  const startX = 26;
  const baseline = height - 42;

  bars.forEach((bar, index) => {
    const x = startX + index * (barWidth + gap);
    const barHeight = (bar.value / maxValue) * (height - 78);
    const y = baseline - barHeight;
    ctx.fillStyle = bar.color;
    ctx.fillRect(x, y, barWidth, barHeight);
    ctx.fillStyle = "#122233";
    ctx.font = "12px sans-serif";
    ctx.fillText(bar.label, x + 6, baseline + 16);
    ctx.fillText(String(bar.value), x + 22, y - 8);
  });

  const failures = Object.entries(failureData?.failure_summary || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2);

  ctx.fillStyle = "#122233";
  ctx.font = "12px sans-serif";
  failures.forEach(([name, count], idx) => {
    ctx.fillText(`${name}: ${count}`, 300, 28 + idx * 16);
  });
}
