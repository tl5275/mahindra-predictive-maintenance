"""Redis-backed fleet state repository for latest telemetry and alerts."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

import redis

from core.config import get_settings
from services.fleet_view import alert_sort_key, build_alert_vehicle, normalize_vehicle_record


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


class FleetStateRepository:
    """Small Redis repository focused on read/write paths used by the platform."""

    def vehicle_key(self, vehicle_id: str) -> str:
        return f"{settings.redis_vehicle_prefix}:{vehicle_id}"

    def store_processed_batch(
        self,
        redis_client: redis.Redis,
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
        keys = [self.vehicle_key(str(record["vehicle_id"])) for record in normalized_records]
        previous_payloads = redis_client.mget(keys)
        previous_states = {
            str(record["vehicle_id"]): json.loads(payload)
            for record, payload in zip(normalized_records, previous_payloads)
            if payload
        }
        delta_events: list[dict[str, Any]] = []

        pipeline = redis_client.pipeline()
        for record in normalized_records:
            vehicle_id = str(record["vehicle_id"])
            changed_fields = _changed_fields(previous_states.get(vehicle_id), record)
            if changed_fields:
                delta_events.append(
                    {
                        "vehicle_id": vehicle_id,
                        "timestamp": str(record.get("timestamp", batch_timestamp)),
                        "changed_fields": changed_fields,
                    }
                )
            payload = json.dumps(record, separators=(",", ":"))
            pipeline.set(self.vehicle_key(vehicle_id), payload)
            pipeline.zadd(
                settings.redis_fleet_index_key,
                {vehicle_id: _parse_timestamp(str(record.get("timestamp")))},
            )

        if alerts:
            serialized_alerts = [json.dumps(alert, separators=(",", ":")) for alert in alerts]
            pipeline.lpush(settings.redis_alerts_key, *serialized_alerts)
            pipeline.ltrim(settings.redis_alerts_key, 0, settings.recent_alert_limit - 1)

        pipeline.hset(
            settings.redis_metrics_key,
            mapping={
                "last_processed_at": batch_timestamp,
                "last_batch_size": len(normalized_records),
                "last_delta_size": len(delta_events),
                "last_simulator_id": simulator_id,
            },
        )
        pipeline.hincrby(settings.redis_metrics_key, "total_batches", 1)
        pipeline.hincrby(settings.redis_metrics_key, "total_records", len(normalized_records))
        pipeline.execute()

        fleet_size = redis_client.zcard(settings.redis_fleet_index_key)
        redis_client.hset(settings.redis_metrics_key, mapping={"fleet_size": fleet_size})
        live_alerts = [
            alert_vehicle
            for alert_vehicle in (build_alert_vehicle(record) for record in normalized_records)
            if alert_vehicle is not None
        ]
        live_alerts.sort(key=alert_sort_key)
        if not delta_events and not alerts:
            return None

        return {
            "type": "delta_batch",
            "timestamp": batch_timestamp,
            "fleet_size": fleet_size,
            "vehicles": delta_events,
            "alerts": live_alerts[: settings.recent_alert_limit],
        }

    def _load_vehicle_states(
        self,
        redis_client: redis.Redis,
        *,
        vehicle_ids: list[str],
    ) -> list[dict[str, Any]]:
        if not vehicle_ids:
            return []

        payloads = redis_client.mget([self.vehicle_key(vehicle_id) for vehicle_id in vehicle_ids])
        return [normalize_vehicle_record(json.loads(item)) for item in payloads if item]

    def get_fleet_page(
        self,
        redis_client: redis.Redis,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        normalized_status = (status or "all").strip().lower()
        query = (search or "").strip().lower()

        if query or normalized_status != "all":
            vehicle_ids = redis_client.zrevrange(settings.redis_fleet_index_key, 0, -1)
            vehicles = self._load_vehicle_states(redis_client, vehicle_ids=vehicle_ids)
            if query:
                vehicles = [
                    vehicle
                    for vehicle in vehicles
                    if query in f"{vehicle['vehicle_id']} {vehicle.get('model', '')}".lower()
                ]
            if normalized_status in {"healthy", "warning", "critical"}:
                vehicles = [vehicle for vehicle in vehicles if vehicle.get("status") == normalized_status]
            fleet_size = len(vehicles)
            vehicles = vehicles[offset : offset + limit]
        else:
            vehicle_ids = redis_client.zrevrange(settings.redis_fleet_index_key, offset, offset + limit - 1)
            vehicles = self._load_vehicle_states(redis_client, vehicle_ids=vehicle_ids)
            fleet_size = int(redis_client.hget(settings.redis_metrics_key, "fleet_size") or 0)
            if fleet_size == 0:
                fleet_size = redis_client.zcard(settings.redis_fleet_index_key)

        metrics = redis_client.hgetall(settings.redis_metrics_key)
        return {
            "timestamp": metrics.get("last_processed_at"),
            "fleet_size": fleet_size,
            "limit": limit,
            "offset": offset,
            "vehicles": vehicles,
        }

    def get_vehicle_state(self, redis_client: redis.Redis, vehicle_id: str) -> dict[str, Any] | None:
        payload = redis_client.get(self.vehicle_key(vehicle_id))
        if not payload:
            return None
        return normalize_vehicle_record(json.loads(payload))

    def get_recent_alerts(self, redis_client: redis.Redis, limit: int | None = None) -> list[dict[str, Any]]:
        desired = limit or settings.recent_alert_limit
        payloads = redis_client.lrange(settings.redis_alerts_key, 0, max(0, desired - 1))
        return [json.loads(item) for item in payloads]

    def get_alert_vehicles(self, redis_client: redis.Redis, *, limit: int | None = None) -> list[dict[str, Any]]:
        desired = limit or settings.recent_alert_limit
        vehicle_ids = redis_client.zrevrange(settings.redis_fleet_index_key, 0, -1)
        vehicles = self._load_vehicle_states(redis_client, vehicle_ids=vehicle_ids)
        alerts = [
            alert_vehicle
            for alert_vehicle in (build_alert_vehicle(vehicle) for vehicle in vehicles)
            if alert_vehicle is not None
        ]
        alerts.sort(key=alert_sort_key)
        return alerts[:desired]

    def set_client_metrics(self, redis_client: redis.Redis, *, render_time: float, lag_ms: float) -> None:
        redis_client.hset(
            settings.redis_metrics_key,
            mapping={
                "client_render_time": round(float(render_time), 2),
                "client_lag_ms": round(float(lag_ms), 2),
                "client_metrics_at": _utc_now(),
            },
        )

    def get_metrics(self, redis_client: redis.Redis) -> dict[str, Any]:
        metrics = redis_client.hgetall(settings.redis_metrics_key)
        return {
            "last_processed_at": metrics.get("last_processed_at"),
            "last_batch_size": int(metrics.get("last_batch_size", 0)),
            "last_delta_size": int(metrics.get("last_delta_size", 0)),
            "fleet_size": int(metrics.get("fleet_size", 0)),
            "total_batches": int(metrics.get("total_batches", 0)),
            "total_records": int(metrics.get("total_records", 0)),
            "last_simulator_id": metrics.get("last_simulator_id"),
            "client_render_time": float(metrics.get("client_render_time", 0) or 0),
            "client_lag_ms": float(metrics.get("client_lag_ms", 0) or 0),
            "client_metrics_at": metrics.get("client_metrics_at"),
        }


fleet_state_repository = FleetStateRepository()
