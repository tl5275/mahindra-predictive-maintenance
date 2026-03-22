const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

function buildWebSocketUrl() {
  return `${API_URL.replace("http", "ws")}/ws/fleet`;
}

export function connectFleetSocket({ onOpen, onClose, onMessage, onError }) {
  const socket = new WebSocket(buildWebSocketUrl());

  socket.addEventListener("open", () => onOpen?.());
  socket.addEventListener("close", () => onClose?.());
  socket.addEventListener("error", (event) => onError?.(event));
  socket.addEventListener("message", (event) => {
    try {
      const payload = JSON.parse(event.data);
      onMessage?.(payload);
    } catch (error) {
      onError?.(error);
    }
  });

  return socket;
}
