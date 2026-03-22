"""Service for updating and querying digital twins."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Dict, Iterable, Mapping, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from digital_twin.twin_engine import TwinEngine


class TwinService:
    """Wraps the digital twin engine for backend consumption."""

    def __init__(self) -> None:
        self.engine = TwinEngine(history_size=120)

    def update(self, telemetry_batch: Iterable[Mapping[str, object]]) -> Dict[str, Dict[str, object]]:
        return self.engine.update_fleet(telemetry_batch)

    def get_vehicle_twin(self, vehicle_id: str) -> Optional[Dict[str, object]]:
        return self.engine.get_vehicle_twin(vehicle_id)

    def get_fleet_health(self) -> Dict[str, object]:
        return self.engine.fleet_health_summary()


twin_service = TwinService()
