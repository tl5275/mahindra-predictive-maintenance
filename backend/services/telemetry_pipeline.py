"""Local telemetry processing pipeline for POST /telemetry ingestion."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from backend.database.db import session_scope
from backend.database.models import AlertRecord, MaintenanceLog, TelemetryHistory
from backend.services.alert_engine import build_maintenance_logs, evaluate_vehicle_alerts
from backend.services.fleet_view import normalize_vehicle_record
from backend.services.state_service import StateStoreResult, fleet_state_service


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    normalized = str(value or _utc_now()).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _component_scores(record: dict[str, Any]) -> dict[str, float]:
    temp = float(record.get("engine_temperature", 0.0) or 0.0)
    rpm = float(record.get("rpm", 0.0) or 0.0)
    oil = float(record.get("oil_pressure", 60.0) or 60.0)
    battery = float(record.get("battery_health", 100.0) or 100.0)
    brake = float(record.get("brake_wear", 0.0) or 0.0)
    vibration = float(record.get("vibration", 0.0) or 0.0)

    return {
        "engine": max(0.0, (temp - 96.0) * 0.038)
        + max(0.0, (rpm - 2500.0) * 0.00022)
        + max(0.0, (vibration - 1.6) * 0.22),
        "lubrication": max(0.0, (38.0 - oil) * 0.055) + max(0.0, (rpm - 2200.0) * 0.00012),
        "battery": max(0.0, (72.0 - battery) * 0.024),
        "brake": max(0.0, (brake - 45.0) * 0.02),
    }


def _predicted_component(record: dict[str, Any]) -> str:
    scores = _component_scores(record)
    return max(scores, key=scores.get)


def _health_score(record: dict[str, Any]) -> float:
    temp = float(record.get("engine_temperature", 0.0) or 0.0)
    rpm = float(record.get("rpm", 0.0) or 0.0)
    oil = float(record.get("oil_pressure", 60.0) or 60.0)
    battery = float(record.get("battery_health", 100.0) or 100.0)
    brake = float(record.get("brake_wear", 0.0) or 0.0)
    vibration = float(record.get("vibration", 0.0) or 0.0)
    active_failures = list(record.get("active_failures", []) or [])

    penalty = 0.0
    penalty += max(0.0, temp - 95.0) * 1.35
    penalty += max(0.0, rpm - 2600.0) * 0.009
    penalty += max(0.0, 35.0 - oil) * 2.1
    penalty += max(0.0, 65.0 - battery) * 0.9
    penalty += max(0.0, brake - 45.0) * 0.55
    penalty += max(0.0, vibration - 1.4) * 18.0
    penalty += len(active_failures) * 9.0
    return round(_clamp(100.0 - penalty, 5.0, 100.0), 2)


def _anomaly_score(record: dict[str, Any], health_score: float) -> float:
    temp = float(record.get("engine_temperature", 0.0) or 0.0)
    battery = float(record.get("battery_health", 100.0) or 100.0)
    vibration = float(record.get("vibration", 0.0) or 0.0)
    active_failures = list(record.get("active_failures", []) or [])

    score = 0.16 + ((100.0 - health_score) / 100.0) * 0.78
    score += len(active_failures) * 0.07
    if temp >= 110.0 or vibration >= 3.0:
        score = max(score, 0.83)
    elif temp >= 102.0 or vibration >= 2.2 or battery <= 55.0:
        score = max(score, 0.52)
    return round(_clamp(score, 0.02, 0.99), 4)


def _failure_probability(health_score: float, anomaly_score: float, active_failures: list[str]) -> float:
    probability = max(anomaly_score * 0.92, ((100.0 - health_score) / 100.0) * 1.05 + len(active_failures) * 0.05)
    return round(_clamp(probability, 0.02, 0.99), 4)


def _rul_hours(record: dict[str, Any], health_score: float, active_failures: list[str]) -> int:
    temp = float(record.get("engine_temperature", 0.0) or 0.0)
    battery = float(record.get("battery_health", 100.0) or 100.0)
    brake = float(record.get("brake_wear", 0.0) or 0.0)

    estimate = health_score * 6.2
    estimate += max(0.0, battery - 45.0) * 1.4
    estimate -= max(0.0, temp - 90.0) * 4.3
    estimate -= max(0.0, brake - 40.0) * 3.4
    estimate -= len(active_failures) * 36.0
    return int(round(_clamp(estimate, 12.0, 720.0)))


def _maintenance_priority(normalized: dict[str, Any]) -> str:
    if normalized["status"] == "critical" or int(normalized["rul"]) <= 48:
        return "CRITICAL"
    if normalized["status"] == "warning" or int(normalized["rul"]) <= 120:
        return "HIGH"
    if int(normalized["rul"]) <= 240:
        return "MEDIUM"
    return "LOW"


class TelemetryPipeline:
    def _normalize_records(self, payload: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if isinstance(payload, dict) and isinstance(payload.get("records"), list):
            records = payload.get("records", [])
            metadata = {
                "generated_at": payload.get("generated_at", _utc_now()),
                "simulator_id": payload.get("simulator_id"),
            }
        elif isinstance(payload, list):
            records = payload
            metadata = {"generated_at": _utc_now(), "simulator_id": None}
        elif isinstance(payload, dict):
            records = [payload]
            metadata = {"generated_at": payload.get("timestamp", _utc_now()), "simulator_id": payload.get("simulator_id")}
        else:
            raise ValueError("Telemetry payload must be a record, a list of records, or {'records': [...]} format")

        normalized: list[dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            item = dict(record)
            item["vehicle_id"] = str(item.get("vehicle_id", "")).strip()
            if not item["vehicle_id"]:
                continue
            item.setdefault("timestamp", metadata["generated_at"] or _utc_now())
            normalized.append(item)
        return normalized, metadata

    def _enrich_record(self, record: dict[str, Any]) -> dict[str, Any]:
        active_failures = list(record.get("active_failures", []) or [])
        health_score = _health_score(record)
        anomaly_score = _anomaly_score(record, health_score)
        predicted_component = _predicted_component(record)
        failure_probability = _failure_probability(health_score, anomaly_score, active_failures)
        rul_hours = _rul_hours(record, health_score, active_failures)

        normalized = normalize_vehicle_record(
            {
                **record,
                "health_score": health_score,
                "vehicle_health_score": health_score,
                "anomaly_score": anomaly_score,
                "anomaly_flag": anomaly_score >= 0.45,
                "rul_hours": rul_hours,
                "predicted_component": predicted_component,
                "failure_probability": failure_probability,
            }
        )
        return {
            **normalized,
            "predicted_component": predicted_component,
            "failure_probability": failure_probability,
            "maintenance_priority": _maintenance_priority(normalized),
            "maintenance_recommendation": normalized["recommended_action"],
            "remaining_useful_life_hours": normalized["rul"],
        }

    def _persist_batch(
        self,
        records: list[dict[str, Any]],
        alerts: list[dict[str, Any]],
        maintenance_logs: list[dict[str, Any]],
    ) -> None:
        try:
            with session_scope() as session:
                session.add_all(
                    [
                        TelemetryHistory(
                            vehicle_id=str(record["vehicle_id"]),
                            timestamp=_as_datetime(str(record.get("timestamp"))),
                            model=str(record.get("model", "Mahindra Fleet Vehicle")),
                            driving_mode=str(record.get("driving_mode", "city")),
                            rpm=float(record.get("rpm", 0.0)),
                            engine_temperature=float(record.get("engine_temperature", 0.0)),
                            oil_pressure=float(record.get("oil_pressure", 0.0)),
                            brake_wear=float(record.get("brake_wear", 0.0)),
                            battery_health=float(record.get("battery_health", 0.0)),
                            vibration=float(record.get("vibration", 0.0)),
                            speed_kmph=float(record.get("speed_kmph", 0.0)),
                            odometer_km=float(record.get("odometer_km", 0.0)),
                            latitude=float(record.get("latitude", 0.0)),
                            longitude=float(record.get("longitude", 0.0)),
                            anomaly_score=float(record.get("anomaly_score", 0.0)),
                            anomaly_flag=bool(record.get("anomaly_flag", False)),
                            rul_hours=int(record.get("rul_hours", record.get("rul", 0))),
                            health_score=float(record.get("health_score", record.get("health", 100.0))),
                            health_status=str(record.get("health_status", record.get("status", "healthy"))),
                            active_failures=list(record.get("active_failures", [])),
                            payload=record,
                        )
                        for record in records
                    ]
                )
                session.add_all(
                    [
                        AlertRecord(
                            alert_id=str(alert["alert_id"]),
                            vehicle_id=str(alert["vehicle_id"]),
                            alert_type=str(alert["alert_type"]),
                            severity=str(alert["severity"]),
                            message=str(alert["message"]),
                            anomaly_score=float(alert["anomaly_score"]) if alert.get("anomaly_score") is not None else None,
                            rul_hours=int(alert["rul_hours"]) if alert.get("rul_hours") is not None else None,
                            recommended_action=alert.get("recommended_action"),
                            details=dict(alert.get("metadata", {})),
                            created_at=_as_datetime(str(alert["created_at"])),
                        )
                        for alert in alerts
                    ]
                )
                session.add_all(
                    [
                        MaintenanceLog(
                            external_id=str(log["metadata"].get("alert_id")) if log.get("metadata", {}).get("alert_id") else None,
                            vehicle_id=str(log["vehicle_id"]),
                            event_type=str(log["event_type"]),
                            priority=str(log["priority"]),
                            description=str(log["description"]),
                            status=str(log.get("status", "open")),
                            scheduled_within_hours=log.get("scheduled_within_hours"),
                            details=dict(log.get("metadata", {})),
                        )
                        for log in maintenance_logs
                    ]
                )
        except SQLAlchemyError:
            return

    def process(self, payload: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], StateStoreResult]:
        raw_records, metadata = self._normalize_records(payload)
        processed_records = [self._enrich_record(record) for record in raw_records]

        alerts: list[dict[str, Any]] = []
        for record in processed_records:
            record_alerts = evaluate_vehicle_alerts(record)
            for alert in record_alerts:
                alert.setdefault("metadata", {})
                alert["metadata"]["alert_id"] = alert["alert_id"]
            alerts.extend(record_alerts)

        maintenance_logs = build_maintenance_logs(alerts)
        self._persist_batch(processed_records, alerts, maintenance_logs)
        state_result = fleet_state_service.store_processed_batch(processed_records, alerts, metadata=metadata)
        return processed_records, alerts, state_result


telemetry_pipeline = TelemetryPipeline()
