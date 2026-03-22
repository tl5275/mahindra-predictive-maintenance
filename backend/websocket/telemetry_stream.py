"""WebSocket connection manager for live fleet delta updates."""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timezone
import time
from typing import Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.config import get_settings


router = APIRouter(tags=["WebSocket"])
settings = get_settings()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp_ms(value: Optional[str]) -> float:
    if not value:
        return time.time() * 1000
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).timestamp() * 1000
    except ValueError:
        return time.time() * 1000


class TelemetryBroadcaster:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._connections_lock = asyncio.Lock()
        self._rate_window: deque[tuple[float, int, int]] = deque()
        self._stats: dict[str, Any] = {
            "messages_sent": 0,
            "dropped_updates": 0,
            "last_batch_size": 0,
            "last_lag_ms": 0.0,
            "last_broadcast_at": None,
        }
        self._client_metrics: dict[str, Any] = {
            "render_time": 0.0,
            "lag_ms": 0.0,
            "updated_at": None,
        }

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def register(self, websocket: WebSocket) -> None:
        async with self._connections_lock:
            self._connections.add(websocket)

    async def unregister(self, websocket: WebSocket) -> None:
        async with self._connections_lock:
            self._connections.discard(websocket)

    def record_client_metrics(self, *, render_time: float, lag_ms: float) -> None:
        self._client_metrics = {
            "render_time": round(float(render_time), 2),
            "lag_ms": round(float(lag_ms), 2),
            "updated_at": _utc_now(),
        }

    def snapshot(self) -> dict[str, Any]:
        now = time.monotonic()
        self._prune_rate_window(now)
        window_seconds = 10.0
        total_messages = sum(entry[1] for entry in self._rate_window)
        total_vehicle_updates = sum(entry[2] for entry in self._rate_window)
        messages_per_sec = total_messages / window_seconds if window_seconds else 0.0
        vehicle_updates_per_sec = total_vehicle_updates / window_seconds if window_seconds else 0.0
        return {
            "ws_connections": len(self._connections),
            "messages_per_sec": round(messages_per_sec, 2),
            "vehicle_updates_per_sec": round(vehicle_updates_per_sec, 2),
            "pending_updates": 0,
            "dropped_updates": int(self._stats["dropped_updates"]),
            "last_batch_size": int(self._stats["last_batch_size"]),
            "batches_sent": int(self._stats["messages_sent"]),
            "last_broadcast_at": self._stats["last_broadcast_at"],
            "relay_lag_ms": round(float(self._stats["last_lag_ms"]), 2),
            "render_time": round(float(self._client_metrics["render_time"]), 2),
            "lag_ms": round(max(float(self._stats["last_lag_ms"]), float(self._client_metrics["lag_ms"])), 2),
            "client_metrics_at": self._client_metrics["updated_at"],
        }

    async def broadcast(self, payload: dict[str, Any]) -> None:
        lag_ms = self._batch_lag_ms(payload)
        message = {**payload, "lag_ms": lag_ms}

        async with self._connections_lock:
            connections = list(self._connections)

        self._stats["last_lag_ms"] = lag_ms
        self._stats["last_broadcast_at"] = _utc_now()
        self._stats["last_batch_size"] = len(payload.get("vehicles", []))

        if connections:
            await asyncio.gather(
                *(self._send_safe(websocket, message) for websocket in connections),
                return_exceptions=True,
            )

        self._stats["messages_sent"] = int(self._stats["messages_sent"]) + 1
        self._rate_window.append((time.monotonic(), 1, len(payload.get("vehicles", []))))
        self._prune_rate_window(time.monotonic())

    async def _send_safe(self, websocket: WebSocket, payload: dict[str, Any]) -> None:
        try:
            await websocket.send_json(payload)
        except Exception:
            await self.unregister(websocket)

    def _batch_lag_ms(self, payload: dict[str, Any]) -> float:
        vehicle_updates = payload.get("vehicles", [])
        if not vehicle_updates:
            return 0.0
        oldest_update_ms = min(_timestamp_ms(update.get("timestamp")) for update in vehicle_updates)
        return max(0.0, round((time.time() * 1000) - oldest_update_ms, 2))

    def _prune_rate_window(self, now: float) -> None:
        while self._rate_window and now - self._rate_window[0][0] > 10.0:
            self._rate_window.popleft()


telemetry_broadcaster = TelemetryBroadcaster()


async def _stream_fleet_updates(websocket: WebSocket) -> None:
    await telemetry_broadcaster.start()
    await websocket.accept()
    await telemetry_broadcaster.register(websocket)
    await websocket.send_json(
        {
            "type": "connected",
            "channel": "/ws/fleet",
            "batch_interval_ms": settings.websocket_batch_interval_ms,
        }
    )

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await telemetry_broadcaster.unregister(websocket)


@router.websocket("/ws")
async def stream_root(websocket: WebSocket) -> None:
    await _stream_fleet_updates(websocket)


@router.websocket("/ws/fleet")
async def stream_fleet(websocket: WebSocket) -> None:
    await _stream_fleet_updates(websocket)


@router.websocket("/ws/telemetry")
async def stream_telemetry(websocket: WebSocket) -> None:
    await _stream_fleet_updates(websocket)
