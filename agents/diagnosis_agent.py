"""Rule-based diagnostics for component failures."""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping


class DiagnosisAgent:
    """Detects likely component failures from telemetry and twin scores."""

    def diagnose(
        self,
        telemetry_batch: Iterable[Mapping[str, object]],
        twin_states: Mapping[str, Mapping[str, object]],
    ) -> List[Dict[str, object]]:
        diagnoses: List[Dict[str, object]] = []

        for telemetry in telemetry_batch:
            vehicle_id = str(telemetry["vehicle_id"])
            twin = twin_states.get(vehicle_id, {})
            issues: List[Dict[str, str]] = []

            engine_temp = float(telemetry["engine_temperature"])
            oil_pressure = float(telemetry["oil_pressure"])
            brake_wear = float(telemetry["brake_wear"])
            battery_health = float(telemetry["battery_health"])

            if engine_temp > 112 or oil_pressure < 28:
                issues.append({"component": "engine", "issue": "critical_engine_stress", "severity": "critical"})
            elif engine_temp > 103 or oil_pressure < 35:
                issues.append({"component": "engine", "issue": "engine_degradation", "severity": "warning"})

            if brake_wear > 88:
                issues.append({"component": "brake", "issue": "immediate_brake_replacement", "severity": "critical"})
            elif brake_wear > 75:
                issues.append({"component": "brake", "issue": "brake_service_due", "severity": "warning"})

            if battery_health < 35:
                issues.append({"component": "battery", "issue": "battery_failure_risk", "severity": "critical"})
            elif battery_health < 55:
                issues.append({"component": "battery", "issue": "battery_degradation", "severity": "warning"})

            if issues:
                diagnoses.append(
                    {
                        "vehicle_id": vehicle_id,
                        "model": telemetry["model"],
                        "health_status": twin.get("vehicle_health_status", "unknown"),
                        "issues": issues,
                    }
                )

        return diagnoses
