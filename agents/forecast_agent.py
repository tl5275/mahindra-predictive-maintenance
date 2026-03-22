"""Fleet maintenance demand forecasting agent."""

from __future__ import annotations

from collections import Counter
from typing import Dict, Iterable, List, Mapping


class ForecastAgent:
    """Predict maintenance demand over short horizons from fleet diagnostics."""

    def predict(
        self,
        diagnoses: Iterable[Mapping[str, object]],
        twin_states: Mapping[str, Mapping[str, object]],
    ) -> Dict[str, object]:
        severity_counter: Counter[str] = Counter()
        model_counter: Counter[str] = Counter()

        for diagnosis in diagnoses:
            model = str(diagnosis["model"])
            model_counter[model] += 1
            for issue in diagnosis["issues"]:  # type: ignore[index]
                severity_counter[str(issue["severity"])] += 1

        total_vehicles = max(1, len(twin_states))
        critical = severity_counter.get("critical", 0)
        warning = severity_counter.get("warning", 0)

        next_day = int(round((critical * 0.60) + (warning * 0.35)))
        next_week = int(round((critical * 2.10) + (warning * 1.40)))

        utilization = round(((critical + warning) / total_vehicles) * 100, 2)

        return {
            "severity_breakdown": dict(severity_counter),
            "affected_models": dict(model_counter),
            "predicted_jobs_next_24h": next_day,
            "predicted_jobs_next_7d": next_week,
            "service_utilization_percent": utilization,
        }
