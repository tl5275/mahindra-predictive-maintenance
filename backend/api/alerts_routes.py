"""Alert endpoints backed by Redis and Postgres."""

from __future__ import annotations

from fastapi import APIRouter, Query

from backend.services.state_service import fleet_state_service


router = APIRouter(tags=["Alerts"])


@router.get("/alerts")
def get_alerts(
    limit: int = Query(default=25, ge=1, le=200),
) -> dict:
    alerts = fleet_state_service.get_alert_vehicles(limit=limit)
    return {
        "count": len(alerts),
        "alerts": alerts,
    }
