"""In-memory latest-state repository used when Redis is unavailable locally."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any

from backend.core.config import get_settings
from backend.services.fleet_view import alert_sort_key, build_alert_vehicle, normalize_vehicle_record


settings = get_settings()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_timestamp(value: str | None) -> float:
    if not value:
        return datetime.now(timezone.utc).timestamp()
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return datetime.now(timezone.utc).timestamp()


def _changed_fields(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    if previous is None:
        return {key: value for key, value in current.items() if key != "vehicle_id"}

    delta: dict[str, Any] = {}
    for key, value in current.items():
        if key == "vehicle_id":
            continue
        if previous.get(key) != value:
            delta[key] = value
    return delta


class InMemoryFleetStateRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self._vehicles: dict[str, dict[str, Any]] = {}
        self._recent_alert_events: list[dict[str, Any]] = []
        self._metrics: dict[str, Any] = {
            "last_processed_at": None,
            "last_batch_size": 0,
            "last_delta_size": 0,
            "fleet_size": 0,
            "total_batches": 0,
            "total_records": 0,
            "last_simulator_id": None,
            "client_render_time": 0.0,
            "client_lag_ms": 0.0,
            "client_metrics_at": None,
        }

    def store_processed_batch(
        self,
        records: list[dict[str, Any]],
        alerts: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if not records:
            return None

        normalized_records = [normalize_vehicle_record(record) for record in records]
        batch_timestamp = str(
            metadata.get("generated_at") if metadata else normalized_records[-1].get("timestamp", _utc_now())
        )
        simulator_id = str(metadata.get("simulator_id", settings.simulator_id)) if metadata else settings.simulator_id

        with self._lock:
            delta_events: list[dict[str, Any]] = []
            for record in normalized_records:
                vehicle_id = str(record["vehicle_id"])
                previous_state = self._vehicles.get(vehicle_id)
                changed_fields = _changed_fields(previous_state, record)
                if changed_fields:
                    delta_events.append(
                        {
                            "vehicle_id": vehicle_id,
                            "timestamp": str(record.get("timestamp", batch_timestamp)),
                            "changed_fields": changed_fields,
                        }
                    )
                self._vehicles[vehicle_id] = record

            if alerts:
                self._recent_alert_events = [*alerts, *self._recent_alert_events][: settings.recent_alert_limit]

            self._metrics["last_processed_at"] = batch_timestamp
            self._metrics["last_batch_size"] = len(normalized_records)
            self._metrics["last_delta_size"] = len(delta_events)
            self._metrics["last_simulator_id"] = simulator_id
            self._metrics["total_batches"] += 1
            self._metrics["total_records"] += len(normalized_records)
            self._metrics["fleet_size"] = len(self._vehicles)

            live_alerts = [
                alert_vehicle
                for alert_vehicle in (build_alert_vehicle(record) for record in self._vehicles.values())
                if alert_vehicle is not None
            ]
            live_alerts.sort(key=alert_sort_key)

            if not delta_events and not live_alerts:
                return None

            return {
                "type": "delta_batch",
                "timestamp": batch_timestamp,
                "fleet_size": len(self._vehicles),
                "vehicles": delta_events,
                "alerts": live_alerts[: settings.recent_alert_limit],
            }

    def get_fleet_page(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        normalized_status = (status or "all").strip().lower()
        query = (search or "").strip().lower()

        with self._lock:
            vehicles = sorted(
                self._vehicles.values(),
                key=lambda item: _parse_timestamp(str(item.get("timestamp"))),
                reverse=True,
            )
            if query:
                vehicles = [
                    vehicle
                    for vehicle in vehicles
                    if query in f"{vehicle['vehicle_id']} {vehicle.get('model', '')}".lower()
                ]
            if normalized_status in {"healthy", "warning", "critical"}:
                vehicles = [vehicle for vehicle in vehicles if vehicle.get("status") == normalized_status]

            fleet_size = len(vehicles)
            page = vehicles[offset : offset + limit]
            return {
                "timestamp": self._metrics["last_processed_at"],
                "fleet_size": fleet_size,
                "limit": limit,
                "offset": offset,
                "vehicles": page,
            }

    def get_vehicle_state(self, vehicle_id: str) -> dict[str, Any] | None:
        with self._lock:
            vehicle = self._vehicles.get(vehicle_id)
            return None if vehicle is None else dict(vehicle)

    def get_recent_alerts(self, limit: int | None = None) -> list[dict[str, Any]]:
        with self._lock:
            desired = limit or settings.recent_alert_limit
            return [dict(alert) for alert in self._recent_alert_events[:desired]]

    def get_alert_vehicles(self, *, limit: int | None = None) -> list[dict[str, Any]]:
        desired = limit or settings.recent_alert_limit
        with self._lock:
            alerts = [
                alert_vehicle
                for alert_vehicle in (build_alert_vehicle(vehicle) for vehicle in self._vehicles.values())
                if alert_vehicle is not None
            ]
            alerts.sort(key=alert_sort_key)
            return alerts[:desired]

    def set_client_metrics(self, *, render_time: float, lag_ms: float) -> None:
        with self._lock:
            self._metrics["client_render_time"] = round(float(render_time), 2)
            self._metrics["client_lag_ms"] = round(float(lag_ms), 2)
            self._metrics["client_metrics_at"] = _utc_now()

    def get_metrics(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._metrics)


memory_state_repository = InMemoryFleetStateRepository()
