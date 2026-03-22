function formatFailures(failures) {
  if (!failures || failures.length === 0) {
    return "No active failures";
  }
  return failures.slice(0, 2).join(", ");
}

export function renderVehicleCard(vehicle, isSelected = false) {
  const twin = vehicle.twin_state || {};
  const status = twin.vehicle_health_status || "healthy";
  const health = twin.vehicle_health_score ?? 100;
  const selectedClass = isSelected ? "selected" : "";

  return `
    <article class="vehicle-card ${selectedClass}" data-vehicle-id="${vehicle.vehicle_id}">
      <strong>${vehicle.vehicle_id}</strong>
      <div class="small">${vehicle.model} | ${vehicle.driving_mode}</div>
      <span class="tag ${status}">${status.toUpperCase()}</span>
      <div class="stat-row"><span>Health</span><strong>${health.toFixed(1)}</strong></div>
      <div class="stat-row"><span>Engine Temp</span><span>${vehicle.engine_temperature.toFixed(1)} C</span></div>
      <div class="stat-row"><span>Brake Wear</span><span>${vehicle.brake_wear.toFixed(1)}%</span></div>
      <div class="stat-row"><span>Battery</span><span>${vehicle.battery_health.toFixed(1)}%</span></div>
      <div class="small" style="margin-top: 6px">${formatFailures(vehicle.active_failures)}</div>
    </article>
  `;
}
