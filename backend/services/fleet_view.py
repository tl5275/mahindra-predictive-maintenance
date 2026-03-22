"""Canonical vehicle view helpers shared across backend APIs and streaming."""

from __future__ import annotations

from typing import Any, Optional


CRITICAL_ANOMALY_THRESHOLD = 0.7
WARNING_ANOMALY_THRESHOLD = 0.4


def compute_vehicle_status(anomaly_score: Optional[float]) -> str:
    score = float(anomaly_score or 0.0)
    if score > CRITICAL_ANOMALY_THRESHOLD:
        return "critical"
    if score > WARNING_ANOMALY_THRESHOLD:
        return "warning"
    return "healthy"


def _calibrated_anomaly_score(record: dict[str, Any]) -> float:
    score = float(record.get("anomaly_score", 0.0) or 0.0)
    temp = float(record.get("temp", record.get("engine_temperature", 0.0)) or 0.0)
    vibration = float(record.get("vibration", 0.0) or 0.0)
    battery = float(record.get("battery", record.get("battery_health", 100.0)) or 100.0)
    active_failures = list(record.get("active_failures", []) or [])
    anomaly_flag = bool(record.get("anomaly_flag", False))

    if anomaly_flag:
        score = max(score, 0.45)
    if active_failures:
        score = max(score, min(0.68, 0.48 + (len(active_failures) - 1) * 0.06))
    if temp >= 110 or vibration >= 3.0:
        score = max(score, 0.72)
    elif temp >= 100 or vibration >= 2.4 or battery <= 60:
        score = max(score, 0.46)

    return round(min(score, 0.99), 4)


def _issue_for_vehicle(status: str, anomaly_score: float, temp: float, vibration: float) -> str:
    if status == "critical":
        if temp >= 108:
            return "Engine Overheating"
        if vibration >= 3.2:
            return "High Vibration Detected"
        return "Critical Health Anomaly"
    if status == "warning":
        if temp >= 100:
            return "Temperature Rising"
        if vibration >= 2.4:
            return "Abnormal Vibration Pattern"
        return "Early Health Degradation"
    return "Routine Monitoring"


def _action_for_vehicle(status: str, rul: int, temp: float) -> str:
    if status == "critical":
        if temp >= 108:
            return "Immediate inspection required."
        return "Immediate diagnostic inspection required."
    if status == "warning":
        if rul <= 240:
            return f"Schedule inspection within {rul}h."
        return "Schedule diagnostic inspection in the next service cycle."
    return "Continue routine monitoring."


def normalize_vehicle_record(record: dict[str, Any]) -> dict[str, Any]:
    vehicle_id = str(record.get("vehicle_id", "")).strip()
    model = str(record.get("model") or "Mahindra Fleet Vehicle")
    anomaly_score = _calibrated_anomaly_score(record)
    status = compute_vehicle_status(anomaly_score)
    health = round(float(record.get("health", record.get("health_score", 100.0)) or 0.0), 2)
    rul = int(round(float(record.get("rul", record.get("rul_hours", 0)) or 0.0)))
    temp = round(float(record.get("temp", record.get("engine_temperature", 0.0)) or 0.0), 1)
    vibration = round(float(record.get("vibration", 0.0) or 0.0), 2)
    rpm = int(round(float(record.get("rpm", 0.0) or 0.0)))
    battery = round(float(record.get("battery", record.get("battery_health", 0.0)) or 0.0), 1)
    speed = round(float(record.get("speed", record.get("speed_kmph", 0.0)) or 0.0), 1)
    latitude = float(record.get("latitude", 0.0) or 0.0)
    longitude = float(record.get("longitude", 0.0) or 0.0)
    timestamp = record.get("timestamp")
    issue = _issue_for_vehicle(status, anomaly_score, temp, vibration)
    recommended_action = _action_for_vehicle(status, rul, temp)

    return {
        **record,
        "vehicle_id": vehicle_id,
        "model": model,
        "timestamp": timestamp,
        "health": health,
        "status": status,
        "rul": rul,
        "temp": temp,
        "vibration": vibration,
        "anomaly_score": anomaly_score,
        "rpm": rpm,
        "battery": battery,
        "speed": speed,
        "latitude": latitude,
        "longitude": longitude,
        "issue": issue,
        "recommended_action": recommended_action,
        "health_score": health,
        "health_status": status,
        "rul_hours": rul,
        "engine_temperature": temp,
        "battery_health": battery,
        "speed_kmph": speed,
        "anomaly_flag": bool(record.get("anomaly_flag", status != "healthy") or status != "healthy"),
    }


def build_alert_vehicle(record: dict[str, Any]) -> Optional[dict[str, Any]]:
    normalized = normalize_vehicle_record(record)
    if normalized["status"] == "healthy":
        return None

    return {
        **normalized,
        "severity": normalized["status"],
        "message": normalized["issue"],
        "created_at": normalized.get("timestamp"),
    }


def alert_sort_key(vehicle: dict[str, Any]) -> tuple[int, float, int, str]:
    severity_rank = {"critical": 0, "warning": 1, "healthy": 2}.get(str(vehicle.get("status", "healthy")), 3)
    return (
        severity_rank,
        -float(vehicle.get("anomaly_score", 0.0) or 0.0),
        int(vehicle.get("rul", 0) or 0),
        str(vehicle.get("vehicle_id", "")),
    )
