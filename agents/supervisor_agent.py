"""Supervisor agent that coordinates the swarm of specialized agents."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Dict, Iterable, Mapping

from agents.anomaly_agent import AnomalyAgent
from agents.diagnosis_agent import DiagnosisAgent
from agents.forecast_agent import ForecastAgent
from agents.manufacturing_agent import ManufacturingAgent
from agents.scheduler_agent import SchedulerAgent


class SupervisorAgent:
    """Runs all agents and aggregates results into one analytics payload."""

    def __init__(self, anomaly_window: int = 30, anomaly_z_threshold: float = 2.8) -> None:
        self.diagnosis_agent = DiagnosisAgent()
        self.anomaly_agent = AnomalyAgent(window_size=anomaly_window, z_threshold=anomaly_z_threshold)
        self.forecast_agent = ForecastAgent()
        self.scheduler_agent = SchedulerAgent()
        self.manufacturing_agent = ManufacturingAgent()

    def run(
        self,
        telemetry_batch: Iterable[Mapping[str, object]],
        twin_states: Mapping[str, Mapping[str, object]],
    ) -> Dict[str, object]:
        diagnoses = self.diagnosis_agent.diagnose(telemetry_batch, twin_states)
        anomalies = self.anomaly_agent.detect(telemetry_batch)
        forecast = self.forecast_agent.predict(diagnoses, twin_states)
        schedule = self.scheduler_agent.create_schedule(diagnoses)
        manufacturing_feedback = self.manufacturing_agent.detect_patterns(diagnoses)

        failure_counter: Counter[str] = Counter()
        for diagnosis in diagnoses:
            for issue in diagnosis["issues"]:  # type: ignore[index]
                failure_counter[str(issue["issue"])] += 1

        return {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "diagnoses": diagnoses,
            "anomalies": anomalies,
            "forecast": forecast,
            "schedule": schedule,
            "manufacturing_feedback": manufacturing_feedback,
            "failure_summary": dict(failure_counter),
        }
