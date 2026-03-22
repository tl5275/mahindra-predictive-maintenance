"""Fleet analytics and maintenance insight routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from backend.database.db import state_store
from backend.services.prediction_service import prediction_service
from backend.services.twin_service import twin_service


router = APIRouter(tags=["Analytics"])


@router.get("/fleet/health")
def get_fleet_health() -> dict:
    """Return fleet health distribution from digital twins."""

    summary = twin_service.get_fleet_health()
    return {
        **summary,
        "timestamp": state_store.last_updated,
    }


@router.get("/fleet/failures")
def get_fleet_failures() -> dict:
    """Return active failure analytics from swarm agents."""

    agent_summary = state_store.get_agent_summary()
    return {
        "updated_at": agent_summary.get("updated_at", state_store.last_updated),
        "failure_summary": agent_summary.get("failure_summary", {}),
        "diagnoses_count": len(agent_summary.get("diagnoses", [])),
        "anomalies_count": len(agent_summary.get("anomalies", [])),
        "forecast": agent_summary.get("forecast", {}),
        "schedule": agent_summary.get("schedule", []),
        "manufacturing_feedback": agent_summary.get("manufacturing_feedback", []),
    }


@router.get("/fleet/predictions")
def get_fleet_predictions(limit: int = Query(default=50, ge=1, le=2000)) -> dict:
    """Return AI failure predictions for fleet vehicles."""

    telemetry = state_store.get_latest_telemetry()
    predictions = prediction_service.predict_fleet(telemetry)
    return {
        "timestamp": state_store.last_updated,
        "predictions": predictions[:limit],
    }
