"""Composite health model for combining component digital twins."""

from __future__ import annotations

from typing import Dict, Mapping


def classify_health(score: float) -> str:
    if score >= 80:
        return "healthy"
    if score >= 60:
        return "warning"
    return "critical"


def combine_component_health(components: Mapping[str, Mapping[str, object]]) -> Dict[str, object]:
    """Combine engine, brake and battery component scores into a single score."""

    engine_score = float(components["engine"]["score"])
    brake_score = float(components["brake"]["score"])
    battery_score = float(components["battery"]["score"])

    overall = (engine_score * 0.45) + (brake_score * 0.30) + (battery_score * 0.25)
    overall = round(max(0.0, min(100.0, overall)), 2)

    return {
        "vehicle_health_score": overall,
        "vehicle_health_status": classify_health(overall),
        "components": components,
    }
