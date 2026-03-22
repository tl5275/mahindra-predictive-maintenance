"""Digital twin orchestration for the full fleet."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Deque, Dict, Iterable, List, Mapping, Optional

from digital_twin.battery_twin import BatteryTwin
from digital_twin.brake_twin import BrakeTwin
from digital_twin.engine_twin import EngineTwin
from digital_twin.health_model import combine_component_health


class TwinEngine:
    """Maintains and updates digital twin state for each vehicle."""

    def __init__(self, history_size: int = 90) -> None:
        self.engine_twin = EngineTwin()
        self.brake_twin = BrakeTwin()
        self.battery_twin = BatteryTwin()
        self.history_size = history_size
        self.vehicle_twins: Dict[str, Dict[str, object]] = {}
        self.health_history: Dict[str, Deque[float]] = {}

    def update_vehicle(self, telemetry: Mapping[str, object]) -> Dict[str, object]:
        """Update one vehicle twin and return the computed state."""

        vehicle_id = str(telemetry["vehicle_id"])

        components = {
            "engine": self.engine_twin.calculate_health(telemetry),
            "brake": self.brake_twin.calculate_health(telemetry),
            "battery": self.battery_twin.calculate_health(telemetry),
        }
        health_snapshot = combine_component_health(components)
        health_snapshot["vehicle_id"] = vehicle_id
        health_snapshot["model"] = telemetry["model"]
        health_snapshot["timestamp"] = telemetry.get("timestamp", datetime.now(timezone.utc).isoformat())
        health_snapshot["active_failures"] = list(telemetry.get("active_failures", []))

        if vehicle_id not in self.health_history:
            self.health_history[vehicle_id] = deque(maxlen=self.history_size)
        self.health_history[vehicle_id].append(float(health_snapshot["vehicle_health_score"]))

        health_snapshot["health_trend"] = list(self.health_history[vehicle_id])[-20:]
        self.vehicle_twins[vehicle_id] = health_snapshot
        return health_snapshot

    def update_fleet(self, telemetry_batch: Iterable[Mapping[str, object]]) -> Dict[str, Dict[str, object]]:
        """Update all twins from a telemetry batch."""

        for telemetry in telemetry_batch:
            self.update_vehicle(telemetry)
        return self.vehicle_twins

    def get_vehicle_twin(self, vehicle_id: str) -> Optional[Dict[str, object]]:
        return self.vehicle_twins.get(vehicle_id)

    def fleet_health_summary(self) -> Dict[str, object]:
        if not self.vehicle_twins:
            return {
                "fleet_size": 0,
                "average_health_score": 0.0,
                "status_counts": {"healthy": 0, "warning": 0, "critical": 0},
            }

        scores: List[float] = []
        status_counts = {"healthy": 0, "warning": 0, "critical": 0}
        for twin in self.vehicle_twins.values():
            score = float(twin["vehicle_health_score"])
            status = str(twin["vehicle_health_status"])
            scores.append(score)
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "fleet_size": len(self.vehicle_twins),
            "average_health_score": round(sum(scores) / len(scores), 2),
            "status_counts": status_counts,
        }
