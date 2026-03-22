"""SQLAlchemy models for persistent platform storage."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class VehicleMetadata(Base):
    __tablename__ = "vehicle_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    model: Mapped[str] = mapped_column(String(64))
    simulator_id: Mapped[str] = mapped_column(String(64), default="simulator-1")
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class TelemetryHistory(Base):
    __tablename__ = "telemetry_history"
    __table_args__ = (
        Index("ix_telemetry_history_vehicle_timestamp", "vehicle_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[str] = mapped_column(String(32), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    model: Mapped[str] = mapped_column(String(64))
    driving_mode: Mapped[str] = mapped_column(String(32))
    rpm: Mapped[float] = mapped_column(Float)
    engine_temperature: Mapped[float] = mapped_column(Float)
    oil_pressure: Mapped[float] = mapped_column(Float)
    brake_wear: Mapped[float] = mapped_column(Float)
    battery_health: Mapped[float] = mapped_column(Float)
    vibration: Mapped[float] = mapped_column(Float)
    speed_kmph: Mapped[float] = mapped_column(Float)
    odometer_km: Mapped[float] = mapped_column(Float)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    anomaly_score: Mapped[float] = mapped_column(Float)
    anomaly_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    rul_hours: Mapped[int] = mapped_column(Integer)
    health_score: Mapped[float] = mapped_column(Float)
    health_status: Mapped[str] = mapped_column(String(32))
    active_failures: Mapped[list[str]] = mapped_column(JSON, default=list)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class AlertRecord(Base):
    __tablename__ = "alert_records"
    __table_args__ = (
        Index("ix_alert_records_vehicle_created", "vehicle_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    vehicle_id: Mapped[str] = mapped_column(String(32), index=True)
    alert_type: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    anomaly_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rul_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recommended_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"
    __table_args__ = (
        Index("ix_maintenance_logs_vehicle_created", "vehicle_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(128), unique=True, index=True, nullable=True)
    vehicle_id: Mapped[str] = mapped_column(String(32), index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    priority: Mapped[str] = mapped_column(String(16))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="open")
    scheduled_within_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
