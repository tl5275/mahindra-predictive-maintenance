const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function request(path) {
  const response = await fetch(`${API_URL}${path}`);
  if (!response.ok) {
    throw new Error(`API request failed (${response.status}) for ${path}`);
  }
  return response.json();
}

export function getFleet(limit = 250, offset = 0) {
  return request(`/fleet?limit=${limit}&offset=${offset}`);
}

export function getVehicle(vehicleId, historyLimit = 50) {
  return request(`/vehicle/${vehicleId}?history_limit=${historyLimit}`);
}

export function getAlerts(limit = 25) {
  return request(`/alerts?limit=${limit}`);
}

export function getSystemStatus() {
  return request("/system-status");
}

export function getMetrics() {
  return request("/metrics");
}

export async function postClientMetrics(payload) {
  const response = await fetch(`${API_URL}/metrics/client`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Metrics request failed (${response.status})`);
  }

  return response.json();
}
