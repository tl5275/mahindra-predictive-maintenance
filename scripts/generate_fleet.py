"""Generate and persist an initial fleet snapshot for debugging/data inspection."""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from simulator.fleet_simulator import FleetSimulator


OUTPUT_PATH = PROJECT_ROOT / "data" / "processed_data" / "initial_fleet_snapshot.json"


def main() -> None:
    simulator = FleetSimulator()
    simulator.create_fleet()
    snapshot = simulator.get_fleet_state()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(snapshot, file, indent=2)

    print(f"Wrote {len(snapshot)} vehicles to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
