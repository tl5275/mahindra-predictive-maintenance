"""Digital twin component for brake health."""

from __future__ import annotations

from typing import Dict, Mapping


class BrakeTwin:
    """Computes brake health based on brake wear percentage."""

    def calculate_health(self, telemetry: Mapping[str, object]) -> Dict[str, object]:
        wear = float(telemetry["brake_wear"])
        score = 100.0 - wear
        score = max(0.0, min(100.0, score))

        if wear >= 88:
            status = "critical"
        elif wear >= 75:
            status = "warning"
        else:
            status = "healthy"

        return {
            "score": round(score, 2),
            "status": status,
            "signals": {"brake_wear": wear},
        }
