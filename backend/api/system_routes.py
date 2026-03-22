"""Health and system-status routes."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.database.db import database_health_details, ping_database
from backend.services.state_service import fleet_state_service
from backend.websocket.telemetry_stream import telemetry_broadcaster


router = APIRouter(tags=["System"])


class ClientMetricsPayload(BaseModel):
    render_time: float = Field(ge=0)
    lag_ms: float = Field(ge=0)


@router.get("/health")
def health() -> dict:
    redis_status = fleet_state_service.redis_status()
    postgres_status = "healthy" if ping_database() else "unhealthy"
    return {
        "status": "ok" if postgres_status == "healthy" else "degraded",
        "backend": "running",
        "redis": redis_status,
        "postgres": postgres_status,
        "storage": fleet_state_service.storage_mode(),
    }


@router.get("/healthz")
def healthz() -> dict:
    return health()


@router.get("/health/db")
def db_health() -> dict:
    return database_health_details()


@router.get("/system-status")
def system_status() -> dict:
    metrics = fleet_state_service.get_metrics()
    return {
        "backend": "running",
        "redis": fleet_state_service.redis_status(),
        "postgres": "healthy" if ping_database() else "unhealthy",
        "storage": fleet_state_service.storage_mode(),
        "telemetry_endpoint": "/telemetry",
        "websocket_channel": "/ws/fleet",
        "last_processed_at": metrics["last_processed_at"],
        "fleet_size": metrics["fleet_size"],
        "total_batches": metrics["total_batches"],
        "total_records": metrics["total_records"],
    }


@router.get("/metrics")
def metrics() -> dict:
    redis_metrics = fleet_state_service.get_metrics()
    websocket_metrics = telemetry_broadcaster.snapshot()
    render_time = redis_metrics["client_render_time"]
    lag_ms = max(float(websocket_metrics["relay_lag_ms"]), float(redis_metrics["client_lag_ms"]))
    return {
        "status": "ok",
        "ws_connections": websocket_metrics["ws_connections"],
        "messages_per_sec": websocket_metrics["messages_per_sec"],
        "vehicle_updates_per_sec": websocket_metrics["vehicle_updates_per_sec"],
        "render_time": render_time,
        "lag_ms": round(lag_ms, 2),
        "relay_lag_ms": websocket_metrics["relay_lag_ms"],
        "pending_updates": websocket_metrics["pending_updates"],
        "dropped_updates": websocket_metrics["dropped_updates"],
        "last_batch_size": websocket_metrics["last_batch_size"],
        "fleet_size": redis_metrics["fleet_size"],
        "last_processed_at": redis_metrics["last_processed_at"],
        "last_delta_size": redis_metrics["last_delta_size"],
        "client_metrics_at": redis_metrics["client_metrics_at"],
    }


@router.post("/metrics/client")
def ingest_client_metrics(payload: ClientMetricsPayload) -> dict:
    fleet_state_service.set_client_metrics(render_time=payload.render_time, lag_ms=payload.lag_ms)
    telemetry_broadcaster.record_client_metrics(render_time=payload.render_time, lag_ms=payload.lag_ms)
    return {"status": "ok"}


@router.get("/system/status")
def system_status_legacy() -> dict:
    return system_status()
