"""Vehicle details endpoints backed by Redis and Postgres."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.database.db import get_db_session
from backend.database.models import AlertRecord, MaintenanceLog, TelemetryHistory
from backend.services.fleet_view import normalize_vehicle_record
from backend.services.state_service import fleet_state_service


router = APIRouter(prefix="/vehicle", tags=["Vehicle"])
settings = get_settings()


def _history_point(row: TelemetryHistory) -> dict:
    return {
        "timestamp": row.timestamp,
        "rpm": row.rpm,
        "engine_temperature": row.engine_temperature,
        "battery_health": row.battery_health,
        "vibration": row.vibration,
        "anomaly_score": row.anomaly_score,
        "rul_hours": row.rul_hours,
        "speed_kmph": row.speed_kmph,
    }


@router.get("/{vehicle_id}")
def get_vehicle(
    vehicle_id: str,
    history_limit: int = Query(default=settings.vehicle_history_limit, ge=5, le=200),
    db: Session = Depends(get_db_session),
) -> dict:
    latest = fleet_state_service.get_vehicle_state(vehicle_id)
    if latest is None:
        raise HTTPException(status_code=404, detail=f"Vehicle {vehicle_id} not found")

    history_rows = []
    alert_rows = []
    maintenance_rows = []
    try:
        history_rows = (
            db.execute(
                select(TelemetryHistory)
                .where(TelemetryHistory.vehicle_id == vehicle_id)
                .order_by(desc(TelemetryHistory.timestamp))
                .limit(history_limit)
            )
            .scalars()
            .all()
        )
        alert_rows = (
            db.execute(
                select(AlertRecord)
                .where(AlertRecord.vehicle_id == vehicle_id)
                .order_by(desc(AlertRecord.created_at))
                .limit(20)
            )
            .scalars()
            .all()
        )
        maintenance_rows = (
            db.execute(
                select(MaintenanceLog)
                .where(MaintenanceLog.vehicle_id == vehicle_id)
                .order_by(desc(MaintenanceLog.created_at))
                .limit(20)
            )
            .scalars()
            .all()
        )
    except SQLAlchemyError:
        history_rows = []
        alert_rows = []
        maintenance_rows = []

    return {
        "latest": normalize_vehicle_record(latest),
        "alerts": [
            {
                "alert_id": row.alert_id,
                "vehicle_id": row.vehicle_id,
                "alert_type": row.alert_type,
                "severity": row.severity,
                "message": row.message,
                "created_at": row.created_at,
                "anomaly_score": row.anomaly_score,
                "rul_hours": row.rul_hours,
                "recommended_action": row.recommended_action,
                "metadata": row.details,
            }
            for row in alert_rows
        ],
        "maintenance_logs": [
            {
                "event_type": row.event_type,
                "priority": row.priority,
                "description": row.description,
                "status": row.status,
                "scheduled_within_hours": row.scheduled_within_hours,
                "created_at": row.created_at,
                "metadata": row.details,
            }
            for row in maintenance_rows
        ],
        "history": [_history_point(row) for row in reversed(history_rows)],
    }
