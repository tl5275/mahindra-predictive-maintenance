"""Service scheduling agent for prioritized maintenance actions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Mapping


class SchedulerAgent:
    """Creates appointment recommendations from diagnosis output."""

    SERVICE_CENTERS = ["Pune", "Nashik", "Jaipur", "Bengaluru", "Chennai"]

    def create_schedule(self, diagnoses: Iterable[Mapping[str, object]]) -> List[Dict[str, object]]:
        prioritized: List[Dict[str, object]] = []

        for diagnosis in diagnoses:
            max_severity = "warning"
            if any(issue["severity"] == "critical" for issue in diagnosis["issues"]):  # type: ignore[index]
                max_severity = "critical"
            prioritized.append(
                {
                    "vehicle_id": diagnosis["vehicle_id"],
                    "model": diagnosis["model"],
                    "severity": max_severity,
                    "issues": diagnosis["issues"],
                }
            )

        prioritized.sort(key=lambda item: item["severity"] != "critical")

        now = datetime.now(timezone.utc)
        appointments: List[Dict[str, object]] = []
        for index, item in enumerate(prioritized[:40]):
            slot = now + timedelta(hours=(index * 2))
            center = self.SERVICE_CENTERS[index % len(self.SERVICE_CENTERS)]
            appointments.append(
                {
                    "vehicle_id": item["vehicle_id"],
                    "model": item["model"],
                    "severity": item["severity"],
                    "service_center": center,
                    "appointment_time": slot.isoformat(),
                }
            )

        return appointments
