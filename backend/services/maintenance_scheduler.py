"""Automated maintenance scheduling based on RUL and risk."""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping


def priority_from_rul(remaining_hours: int) -> str:
    if remaining_hours < 24:
        return "CRITICAL"
    if remaining_hours < 72:
        return "HIGH"
    if remaining_hours < 168:
        return "MEDIUM"
    return "LOW"


def service_window_from_priority(priority: str) -> int:
    windows = {
        "CRITICAL": 12,
        "HIGH": 24,
        "MEDIUM": 72,
        "LOW": 168,
    }
    return windows.get(priority, 168)


def recommended_action(component: str) -> str:
    actions = {
        "engine": "cooling system inspection",
        "lubrication": "oil circuit pressure check",
        "battery": "battery and charging system diagnostics",
        "brake": "brake pad and hydraulic inspection",
    }
    return actions.get(component, "general system inspection")


def build_service_recommendation(
    vehicle_id: str,
    component: str,
    failure_probability: float,
    remaining_useful_life_hours: int,
) -> Dict[str, object]:
    priority = priority_from_rul(remaining_useful_life_hours)
    return {
        "vehicle_id": vehicle_id,
        "component": component,
        "failure_probability": round(float(failure_probability), 4),
        "remaining_useful_life_hours": int(remaining_useful_life_hours),
        "priority": priority,
        "recommended_action": recommended_action(component),
        "recommended_service_window_hours": service_window_from_priority(priority),
    }


def generate_service_plan(
    enriched_predictions: Iterable[Mapping[str, object]],
    top_n: int = 20,
) -> List[Dict[str, object]]:
    plans = [
        build_service_recommendation(
            vehicle_id=str(item["vehicle_id"]),
            component=str(item.get("predicted_component", "engine")),
            failure_probability=float(item.get("failure_probability", 0.0)),
            remaining_useful_life_hours=int(item.get("remaining_useful_life_hours", 720)),
        )
        for item in enriched_predictions
    ]

    priority_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    plans.sort(
        key=lambda plan: (
            priority_rank.get(str(plan["priority"]), 99),
            int(plan["remaining_useful_life_hours"]),
            -float(plan["failure_probability"]),
        )
    )
    return plans[:top_n]
