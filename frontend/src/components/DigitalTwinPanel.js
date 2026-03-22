function componentRow(label, score, status) {
  return `
    <div class="stat-row">
      <span>${label}</span>
      <span><strong>${score?.toFixed?.(1) ?? score}</strong> <span class="tag ${status}">${status}</span></span>
    </div>
  `;
}

export function renderDigitalTwinPanel(vehicleDetails) {
  if (!vehicleDetails || !vehicleDetails.twin_state) {
    return `<h2>Vehicle Digital Twin</h2><p class="small">Select a vehicle to inspect twin health.</p>`;
  }

  const twin = vehicleDetails.twin_state;
  const components = twin.components || {};
  return `
    <h2>Vehicle Digital Twin</h2>
    <div class="small">${vehicleDetails.telemetry.vehicle_id} | ${vehicleDetails.telemetry.model}</div>
    <div class="stat-row" style="margin-top: 8px">
      <span>Overall Health</span>
      <strong>${(twin.vehicle_health_score ?? 0).toFixed(1)}</strong>
    </div>
    <span class="tag ${twin.vehicle_health_status || "healthy"}">${(twin.vehicle_health_status || "healthy").toUpperCase()}</span>
    <div style="margin-top: 8px">
      ${componentRow("Engine", components.engine?.score, components.engine?.status || "healthy")}
      ${componentRow("Brakes", components.brake?.score, components.brake?.status || "healthy")}
      ${componentRow("Battery", components.battery?.score, components.battery?.status || "healthy")}
    </div>
  `;
}
