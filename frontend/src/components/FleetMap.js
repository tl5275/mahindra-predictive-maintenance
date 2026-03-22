export function renderFleetMap(vehicles) {
  if (!vehicles || vehicles.length === 0) {
    return `<p class="small">No fleet data available.</p>`;
  }

  const modeCounts = vehicles.reduce(
    (acc, vehicle) => {
      const mode = vehicle.driving_mode || "unknown";
      acc[mode] = (acc[mode] || 0) + 1;
      return acc;
    },
    { idle: 0, city: 0, highway: 0, heavy_load: 0 }
  );

  const total = vehicles.length;
  const modeBar = (mode, label) => {
    const count = modeCounts[mode] || 0;
    const width = Math.max(1, Math.round((count / total) * 100));
    return `
      <div style="margin-bottom: 6px">
        <div class="small">${label} (${count})</div>
        <div style="height: 8px; background: #eef3f8; border-radius: 999px; overflow: hidden">
          <div style="height: 8px; width: ${width}%; background: linear-gradient(90deg, #0e6b5c, #2f9e88)"></div>
        </div>
      </div>
    `;
  };

  return `
    <h2>Fleet Operating Modes</h2>
    ${modeBar("idle", "Idle")}
    ${modeBar("city", "City")}
    ${modeBar("highway", "Highway")}
    ${modeBar("heavy_load", "Heavy Load")}
  `;
}
