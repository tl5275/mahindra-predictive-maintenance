"""Digital twin component for battery degradation tracking."""

from __future__ import annotations

from typing import Dict, Mapping


class BatteryTwin:
    """Computes battery health score from battery telemetry."""

    def calculate_health(self, telemetry: Mapping[str, object]) -> Dict[str, object]:
        battery_health = float(telemetry["battery_health"])
        temp = float(telemetry["engine_temperature"])

        thermal_penalty = max(0.0, temp - 110.0) * 0.45
        score = max(0.0, min(100.0, battery_health - thermal_penalty))

        if score >= 80:
            status = "healthy"
        elif score >= 55:
            status = "warning"
        else:
            status = "critical"

        return {
            "score": round(score, 2),
            "status": status,
            "signals": {"battery_health": battery_health},
        }
