"""Digital twin component for engine health."""

from __future__ import annotations

from typing import Dict, Mapping


class EngineTwin:
    """Computes engine health from telemetry signals."""

    def calculate_health(self, telemetry: Mapping[str, object]) -> Dict[str, object]:
        rpm = float(telemetry["rpm"])
        temp = float(telemetry["engine_temperature"])
        oil = float(telemetry["oil_pressure"])

        temp_penalty = max(0.0, temp - 95.0) * 1.25
        overheating_penalty = max(0.0, temp - 108.0) * 1.8
        rpm_penalty = max(0.0, rpm - 3500.0) * 0.012
        oil_penalty = max(0.0, 40.0 - oil) * 1.7

        score = 100.0 - temp_penalty - overheating_penalty - rpm_penalty - oil_penalty
        score = max(0.0, min(100.0, score))

        if score >= 80:
            status = "healthy"
        elif score >= 60:
            status = "warning"
        else:
            status = "critical"

        return {
            "score": round(score, 2),
            "status": status,
            "signals": {
                "rpm": rpm,
                "engine_temperature": temp,
                "oil_pressure": oil,
            },
        }
