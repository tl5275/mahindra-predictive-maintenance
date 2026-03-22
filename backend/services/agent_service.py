"""Service layer for running the multi-agent swarm pipeline."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Dict, Iterable, Mapping

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
THRESHOLD_CONFIG_PATH = PROJECT_ROOT / "config" / "thresholds.yaml"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.supervisor_agent import SupervisorAgent


def _load_yaml(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


class AgentService:
    """Runs all swarm agents and stores latest analytics state."""

    def __init__(self) -> None:
        thresholds = _load_yaml(THRESHOLD_CONFIG_PATH).get("anomaly_detection", {})
        self.supervisor = SupervisorAgent(
            anomaly_window=int(thresholds.get("window_size", 30)),
            anomaly_z_threshold=float(thresholds.get("z_score_threshold", 2.8)),
        )
        self.latest_result: Dict[str, object] = {}

    def run(
        self,
        telemetry_batch: Iterable[Mapping[str, object]],
        twin_states: Mapping[str, Mapping[str, object]],
    ) -> Dict[str, object]:
        self.latest_result = self.supervisor.run(telemetry_batch, twin_states)
        return self.latest_result

    def get_latest(self) -> Dict[str, object]:
        return dict(self.latest_result)


agent_service = AgentService()
