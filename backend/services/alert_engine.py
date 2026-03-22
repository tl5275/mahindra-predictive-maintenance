"""Alert evaluation rules for anomaly and remaining-life thresholds."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.core.config import get_settings


settings = get_settings()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _severity_from_anomaly(score: float) -> str:
    if score >= 0.9:
        return "critical"
    if score >= 0.75:
        return "high"
    return "medium"


def _severity_from_rul(rul_hours: int) -> str:
    if rul_hours <= 24:
        return "critical"
    if rul_hours <= 72:
        return "high"
    return "medium"


def evaluate_vehicle_alerts(vehicle_state: dict[str, Any]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    vehicle_id = str(vehicle_state["vehicle_id"])
    created_at = _utc_now()

    anomaly_score = float(vehicle_state.get("anomaly_score", 0.0))
    rul_hours = int(vehicle_state.get("rul_hours", 0))

    if anomaly_score >= settings.anomaly_threshold:
        severity = _severity_from_anomaly(anomaly_score)
        alerts.append(
            {
                "alert_id": f"{vehicle_id}:anomaly:{created_at}",
                "vehicle_id": vehicle_id,
                "alert_type": "anomaly",
                "severity": severity,
                "message": (
                    f"Anomaly score {anomaly_score:.2f} exceeded the threshold "
                    f"of {settings.anomaly_threshold:.2f}."
                ),
                "created_at": created_at,
                "anomaly_score": round(anomaly_score, 4),
                "rul_hours": rul_hours,
                "recommended_action": "Inspect engine, battery, and vibration sensors immediately.",
                "metadata": {
                    "health_status": vehicle_state.get("health_status", "warning"),
                    "active_failures": list(vehicle_state.get("active_failures", [])),
                },
            }
        )

    if rul_hours <= settings.rul_threshold_hours:
        severity = _severity_from_rul(rul_hours)
        alerts.append(
            {
                "alert_id": f"{vehicle_id}:rul:{created_at}",
                "vehicle_id": vehicle_id,
                "alert_type": "rul",
                "severity": severity,
                "message": (
                    f"Remaining useful life dropped to {rul_hours} hours, below the configured "
                    f"threshold of {settings.rul_threshold_hours} hours."
                ),
                "created_at": created_at,
                "anomaly_score": round(anomaly_score, 4),
                "rul_hours": rul_hours,
                "recommended_action": "Schedule preventive maintenance in the next available service window.",
                "metadata": {
                    "predicted_component": vehicle_state.get("predicted_component", "powertrain"),
                },
            }
        )

    return alerts


def build_maintenance_logs(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    logs: list[dict[str, Any]] = []
    for alert in alerts:
        logs.append(
            {
                "vehicle_id": alert["vehicle_id"],
                "event_type": alert["alert_type"],
                "priority": alert["severity"],
                "description": alert["message"],
                "status": "open",
                "scheduled_within_hours": alert.get("rul_hours"),
                "metadata": {
                    "recommended_action": alert.get("recommended_action"),
                    "source": "alert_engine",
                    **dict(alert.get("metadata", {})),
                },
            }
        )
    return logs
