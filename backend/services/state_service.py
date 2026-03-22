"""Fleet state facade that prefers Redis and falls back to in-memory storage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import redis

from core.redis_client import get_sync_redis
from services.memory_state import memory_state_repository
from services.redis_state import fleet_state_repository


@dataclass(frozen=True)
class StateStoreResult:
    payload: Optional[dict[str, Any]]
    storage: str


class FleetStateService:
    def _redis_client(self) -> Optional[redis.Redis]:
        try:
            client = get_sync_redis()
            client.ping()
            return client
        except Exception:
            return None

    def storage_mode(self) -> str:
        return "redis" if self._redis_client() is not None else "memory"

    def redis_status(self) -> str:
        return "healthy" if self._redis_client() is not None else "fallback"

    def store_processed_batch(
        self,
        records: list[dict[str, Any]],
        alerts: list[dict[str, Any]],
        metadata: Optional[dict[str, Any]] = None,
    ) -> StateStoreResult:
        redis_client = self._redis_client()
        if redis_client is not None:
            return StateStoreResult(
                payload=fleet_state_repository.store_processed_batch(
                    redis_client,
                    records,
                    alerts,
                    metadata=metadata,
                ),
                storage="redis",
            )
        return StateStoreResult(
            payload=memory_state_repository.store_processed_batch(records, alerts, metadata),
            storage="memory",
        )

    def get_fleet_page(
        self,
        *,
        limit: int,
        offset: int,
        search: Optional[str] = None,
        status: Optional[str] = None,
    ) -> dict[str, Any]:
        redis_client = self._redis_client()
        if redis_client is not None:
            return fleet_state_repository.get_fleet_page(
                redis_client,
                limit=limit,
                offset=offset,
                search=search,
                status=status,
            )
        return memory_state_repository.get_fleet_page(
            limit=limit,
            offset=offset,
            search=search,
            status=status,
        )

    def get_vehicle_state(self, vehicle_id: str) -> Optional[dict[str, Any]]:
        redis_client = self._redis_client()
        if redis_client is not None:
            return fleet_state_repository.get_vehicle_state(redis_client, vehicle_id)
        return memory_state_repository.get_vehicle_state(vehicle_id)

    def get_recent_alerts(self, limit: Optional[int] = None) -> list[dict[str, Any]]:
        redis_client = self._redis_client()
        if redis_client is not None:
            return fleet_state_repository.get_recent_alerts(redis_client, limit=limit)
        return memory_state_repository.get_recent_alerts(limit=limit)

    def get_alert_vehicles(self, *, limit: Optional[int] = None) -> list[dict[str, Any]]:
        redis_client = self._redis_client()
        if redis_client is not None:
            return fleet_state_repository.get_alert_vehicles(redis_client, limit=limit)
        return memory_state_repository.get_alert_vehicles(limit=limit)

    def set_client_metrics(self, *, render_time: float, lag_ms: float) -> None:
        redis_client = self._redis_client()
        if redis_client is not None:
            fleet_state_repository.set_client_metrics(redis_client, render_time=render_time, lag_ms=lag_ms)
            return
        memory_state_repository.set_client_metrics(render_time=render_time, lag_ms=lag_ms)

    def get_metrics(self) -> dict[str, Any]:
        redis_client = self._redis_client()
        if redis_client is not None:
            return fleet_state_repository.get_metrics(redis_client)
        return memory_state_repository.get_metrics()


fleet_state_service = FleetStateService()
