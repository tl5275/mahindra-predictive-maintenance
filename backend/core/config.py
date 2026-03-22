"""Central runtime settings for the Mahindra platform services."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _csv_env(name: str, default: str) -> tuple[str, ...]:
    value = os.getenv(name, default)
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    project_root: Path
    environment: str
    api_host: str
    api_port: int
    frontend_port: int
    redis_url: str
    redis_vehicle_prefix: str
    redis_fleet_index_key: str
    redis_alerts_key: str
    redis_metrics_key: str
    database_url: str
    cors_origins: tuple[str, ...]
    fleet_page_default: int
    fleet_page_max: int
    vehicle_history_limit: int
    recent_alert_limit: int
    anomaly_threshold: float
    rul_threshold_hours: int
    websocket_batch_interval_ms: int
    simulator_batch_size: int
    simulator_interval_ms: int
    simulator_fleet_size: int
    simulator_id: str
    simulator_api_url: str


@lru_cache
def get_settings() -> Settings:
    default_database_path = (PROJECT_ROOT / "data" / "mahindra_local.db").as_posix()
    return Settings(
        project_root=PROJECT_ROOT,
        environment=os.getenv("ENVIRONMENT", "development"),
        api_host=os.getenv("API_HOST", "0.0.0.0"),
        api_port=int(os.getenv("API_PORT", "8000")),
        frontend_port=int(os.getenv("FRONTEND_PORT", "8080")),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        redis_vehicle_prefix=os.getenv("REDIS_VEHICLE_PREFIX", "fleet:vehicle"),
        redis_fleet_index_key=os.getenv("REDIS_FLEET_INDEX_KEY", "fleet:updated"),
        redis_alerts_key=os.getenv("REDIS_ALERTS_KEY", "fleet:alerts:recent"),
        redis_metrics_key=os.getenv("REDIS_METRICS_KEY", "fleet:metrics"),
        database_url=os.getenv(
            "DATABASE_URL",
            f"sqlite:///{default_database_path}",
        ),
        cors_origins=_csv_env(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:8080,http://127.0.0.1:5173,http://127.0.0.1:8080",
        ),
        fleet_page_default=int(os.getenv("FLEET_PAGE_DEFAULT", "200")),
        fleet_page_max=int(os.getenv("FLEET_PAGE_MAX", "20000")),
        vehicle_history_limit=int(os.getenv("VEHICLE_HISTORY_LIMIT", "50")),
        recent_alert_limit=int(os.getenv("RECENT_ALERT_LIMIT", "100")),
        anomaly_threshold=float(os.getenv("ANOMALY_THRESHOLD", "0.62")),
        rul_threshold_hours=int(os.getenv("RUL_THRESHOLD_HOURS", "120")),
        websocket_batch_interval_ms=int(os.getenv("WEBSOCKET_BATCH_INTERVAL_MS", "200")),
        simulator_batch_size=int(os.getenv("SIMULATOR_BATCH_SIZE", "100")),
        simulator_interval_ms=int(os.getenv("SIMULATOR_INTERVAL_MS", "200")),
        simulator_fleet_size=int(os.getenv("FLEET_SIZE", "10000")),
        simulator_id=os.getenv("SIMULATOR_ID", "simulator-1"),
        simulator_api_url=os.getenv("SIMULATOR_API_URL", f"http://localhost:{os.getenv('API_PORT', '8000')}"),
    )
