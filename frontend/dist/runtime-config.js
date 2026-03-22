window.MAHINDRA_API_BASE = window.MAHINDRA_API_BASE || window.location.origin;
window.MAHINDRA_WS_URL =
  window.MAHINDRA_WS_URL ||
  `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/ws/fleet`;
