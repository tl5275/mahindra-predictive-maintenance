function drawLine(ctx, values, color, minY, maxY, width, height) {
  if (!values.length) return;
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;

  values.forEach((value, idx) => {
    const x = (idx / Math.max(1, values.length - 1)) * width;
    const ratio = (value - minY) / Math.max(1e-6, maxY - minY);
    const y = height - ratio * height;
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

export function drawTelemetryChart(canvas, vehicles) {
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#f8fbfe";
  ctx.fillRect(0, 0, width, height);

  if (!vehicles || !vehicles.length) {
    ctx.fillStyle = "#5d6f81";
    ctx.font = "14px sans-serif";
    ctx.fillText("Waiting for telemetry...", 20, 40);
    return;
  }

  const sample = vehicles.slice(0, 120);
  const tempSeries = sample.map((v) => Number(v.engine_temperature));
  const rpmSeries = sample.map((v) => Number(v.rpm) / 50); // scaled for plotting

  const minY = Math.min(...tempSeries, ...rpmSeries) - 5;
  const maxY = Math.max(...tempSeries, ...rpmSeries) + 5;

  drawLine(ctx, tempSeries, "#c84630", minY, maxY, width, height);
  drawLine(ctx, rpmSeries, "#0e6b5c", minY, maxY, width, height);

  ctx.fillStyle = "#122233";
  ctx.font = "12px sans-serif";
  ctx.fillText("Red: Engine Temp", 14, 18);
  ctx.fillText("Green: RPM / 50", 14, 36);
}
