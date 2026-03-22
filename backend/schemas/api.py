"""Pydantic contracts used by the backend and ML service."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class FleetVehicle(BaseModel):
    model_config = ConfigDict(extra="allow")

    vehicle_id: str
    timestamp: Union[datetime, str]
    model: str
    driving_mode: str
    rpm: float
    engine_temperature: float
    oil_pressure: float
    brake_wear: float
    battery_health: float
    vibration: float
    speed_kmph: float
    odometer_km: float
    latitude: float
    longitude: float
    active_failures: list[str] = Field(default_factory=list)
    anomaly_score: float = 0.0
    anomaly_flag: bool = False
    rul_hours: int = 0
    health_score: float = 100.0
    health_status: str = "healthy"


class FleetResponse(BaseModel):
    timestamp: Optional[Union[datetime, str]] = None
    fleet_size: int
    limit: int
    offset: int
    vehicles: list[FleetVehicle]


class AlertEvent(BaseModel):
    alert_id: str
    vehicle_id: str
    alert_type: str
    severity: str
    message: str
    created_at: Union[datetime, str]
    anomaly_score: Optional[float] = None
    rul_hours: Optional[int] = None
    recommended_action: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VehicleHistoryPoint(BaseModel):
    timestamp: Union[datetime, str]
    rpm: float
    engine_temperature: float
    battery_health: float
    vibration: float
    anomaly_score: float
    rul_hours: int
    speed_kmph: float


class VehicleDetailsResponse(BaseModel):
    latest: FleetVehicle
    alerts: list[AlertEvent] = Field(default_factory=list)
    maintenance_logs: list[dict[str, Any]] = Field(default_factory=list)
    history: list[VehicleHistoryPoint] = Field(default_factory=list)


class SystemStatusResponse(BaseModel):
    backend: str
    redis: str
    postgres: str
    storage: str
    telemetry_endpoint: str
    websocket_channel: str
    last_processed_at: Optional[Union[datetime, str]] = None
    fleet_size: int = 0
    total_batches: int = 0
    total_records: int = 0


class BatchPredictionRequest(BaseModel):
    records: list[dict[str, Any]]


class BatchPredictionResponse(BaseModel):
    records: list[dict[str, Any]]
