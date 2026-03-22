"""Fleet analytics and maintenance insight routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from services.agent_service import agent_service
from services.prediction_service import prediction_service
from services.state_service import fleet_state_service
from services.twin_service import twin_service


router = APIRouter(tags=["Analytics"])


@router.get("/fleet/health")
def get_fleet_health() -> dict:
    """Return fleet health distribution from digital twins."""

    summary = twin_service.get_fleet_health()
    metrics = fleet_state_service.get_metrics()
    return {
        **summary,
        "timestamp": metrics["last_processed_at"],
    }


@router.get("/fleet/failures")
def get_fleet_failures() -> dict:
    """Return active failure analytics from swarm agents."""

    agent_summary = agent_service.get_latest()
    metrics = fleet_state_service.get_metrics()
    return {
        "updated_at": agent_summary.get("updated_at", metrics["last_processed_at"]),
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

    fleet = fleet_state_service.get_fleet_page(limit=20000, offset=0)
    predictions = prediction_service.predict_fleet(fleet["vehicles"])
    return {
        "timestamp": fleet["timestamp"],
        "predictions": predictions[:limit],
    }
