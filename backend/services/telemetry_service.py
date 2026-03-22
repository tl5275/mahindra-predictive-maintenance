"""Service responsible for generating synthetic telemetry batches."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Dict, List

import yaml

from simulator.fleet_simulator import FleetSimulator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SIMULATION_CONFIG_PATH = PROJECT_ROOT / "config" / "simulation_config.yaml"
VEHICLE_MODELS_PATH = PROJECT_ROOT / "config" / "vehicle_models.yaml"


def _load_yaml(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


class TelemetryService:
    """Provides a stable interface between API layer and simulator core."""

    def __init__(self) -> None:
        self.simulation_config = _load_yaml(SIMULATION_CONFIG_PATH)
        self.vehicle_model_config = _load_yaml(VEHICLE_MODELS_PATH)
        self.interval_seconds = float(
            self.simulation_config.get("simulation", {}).get("telemetry_interval_seconds", 1)
        )
        self.simulator = FleetSimulator(
            model_config=self.vehicle_model_config,
            simulation_config=self.simulation_config,
        )
        self.simulator.create_fleet()
        self.recent_updates: Dict[str, Dict[str, object]] = {}

    def tick(self) -> List[Dict[str, object]]:
        """Generate one telemetry batch for all vehicles."""

        batch = self.simulator.step_simulation(dt_seconds=self.interval_seconds)
        self.recent_updates = {str(item["vehicle_id"]): copy.deepcopy(item) for item in batch}
        return batch

    def get_fleet_size(self) -> int:
        return len(self.simulator.vehicles)

    def get_vehicle_state(self, vehicle_id: str) -> Dict[str, object] | None:
        return self.simulator.get_vehicle_state(vehicle_id)

    def get_recent_updates(self) -> List[Dict[str, object]]:
        updates = list(self.recent_updates.values())
        self.recent_updates = {}
        return copy.deepcopy(updates)


telemetry_service = TelemetryService()
