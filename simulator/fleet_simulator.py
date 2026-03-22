"""Fleet simulator that generates batched telemetry and posts it to FastAPI."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
import time
from typing import Dict, List, Mapping, Sequence
import random

import httpx
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIMULATION_CONFIG = PROJECT_ROOT / "config" / "simulation_config.yaml"
DEFAULT_MODEL_CONFIG = PROJECT_ROOT / "config" / "vehicle_models.yaml"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.config import get_settings
from simulator.driving_patterns import get_profile, select_next_mode
from simulator.failure_simulator import FailureSimulator
from simulator.telemetry_generator import TelemetryGenerator
from simulator.vehicle_model import Vehicle


settings = get_settings()


def _weighted_pick(weights: Mapping[str, float], rng: random.Random) -> str:
    roll = rng.random()
    cumulative = 0.0
    for key, weight in weights.items():
        cumulative += float(weight)
        if roll <= cumulative:
            return key
    return next(iter(weights.keys()))


def load_yaml(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


class FleetSimulator:
    """Synthetic fleet simulator for Mahindra vehicle telemetry."""

    def __init__(
        self,
        model_config: Mapping[str, object] | None = None,
        simulation_config: Mapping[str, object] | None = None,
    ) -> None:
        if model_config is None:
            model_config = load_yaml(DEFAULT_MODEL_CONFIG)
        if simulation_config is None:
            simulation_config = load_yaml(DEFAULT_SIMULATION_CONFIG)

        self.model_specs: Dict[str, Mapping[str, float]] = dict(model_config.get("models", {}))
        sim = dict(simulation_config.get("simulation", {}))
        failure_cfg = dict(simulation_config.get("failure_injection", {}))

        self.fleet_size = int(sim.get("fleet_size", settings.simulator_fleet_size))
        self.default_mode = str(sim.get("default_mode", "city"))
        self.model_mix: Dict[str, float] = dict(sim.get("model_mix", {"XUV700": 1.0}))
        self.random = random.Random(int(sim.get("random_seed", 42)))

        self.failure_simulator = FailureSimulator(failure_cfg, seed=int(sim.get("random_seed", 42)) + 1)
        self.telemetry_generator = TelemetryGenerator(seed=int(sim.get("random_seed", 42)) + 2)

        self.vehicles: Dict[str, Vehicle] = {}
        self.last_telemetry: List[Dict[str, object]] = []

    def create_fleet(self) -> Dict[str, Vehicle]:
        self.vehicles.clear()
        for index in range(self.fleet_size):
            model = _weighted_pick(self.model_mix, self.random)
            specs = self.model_specs.get(model, {})
            vehicle = Vehicle(
                vehicle_id=f"MH-{index + 1:06d}",
                model=model,
                rpm=float(specs.get("rpm_idle", 800.0)) + self.random.uniform(-80, 120),
                engine_temperature=float(specs.get("engine_temp_nominal", 94.0)) + self.random.uniform(-3, 3),
                oil_pressure=float(specs.get("oil_pressure_nominal", 56.0)) + self.random.uniform(-2, 2),
                brake_wear=self.random.uniform(0.5, 12.0),
                battery_health=self.random.uniform(82.0, 100.0),
                speed_kmph=self.random.uniform(0.0, 25.0),
                odometer_km=self.random.uniform(50.0, 70000.0),
                driving_mode=self.default_mode,
                latitude=20.0 + self.random.uniform(-8.0, 8.0),
                longitude=78.0 + self.random.uniform(-7.0, 7.0),
                heading_deg=self.random.uniform(0.0, 360.0),
            )
            self.vehicles[vehicle.vehicle_id] = vehicle
        return self.vehicles

    def step_vehicle_batch(self, vehicle_ids: Sequence[str], dt_seconds: float = 1.0) -> List[Dict[str, object]]:
        if not self.vehicles:
            self.create_fleet()

        now = datetime.now(timezone.utc)
        states: List[Dict[str, object]] = []
        effects_by_vehicle: Dict[str, Mapping[str, float]] = {}

        for vehicle_id in vehicle_ids:
            vehicle = self.vehicles[vehicle_id]
            vehicle.driving_mode = select_next_mode(vehicle.driving_mode, self.random)
            profile = get_profile(vehicle.driving_mode)

            pre_state = vehicle.to_dict()
            failure_state = self.failure_simulator.step_vehicle(pre_state)
            vehicle.active_failures = list(failure_state["active_failures"])  # type: ignore[arg-type]

            vehicle.step(
                dt_seconds=dt_seconds,
                profile=profile,
                model_spec=self.model_specs.get(vehicle.model, {}),
                failure_effects=failure_state["effects"],  # type: ignore[arg-type]
                rng=self.random,
            )

            state = vehicle.to_dict()
            states.append(state)
            effects_by_vehicle[vehicle.vehicle_id] = failure_state["effects"]  # type: ignore[index]

        self.last_telemetry = self.telemetry_generator.generate_batch(
            vehicle_states=states,
            effects_by_vehicle=effects_by_vehicle,
            timestamp=now,
        )
        return self.last_telemetry

    def step_simulation(self, dt_seconds: float = 1.0) -> List[Dict[str, object]]:
        return self.step_vehicle_batch(list(self.vehicles.keys()) or list(self.create_fleet().keys()), dt_seconds)

    def get_fleet_state(self) -> List[Dict[str, object]]:
        return [vehicle.to_dict() for vehicle in self.vehicles.values()]

    def get_vehicle_state(self, vehicle_id: str) -> Dict[str, object] | None:
        vehicle = self.vehicles.get(vehicle_id)
        return None if vehicle is None else vehicle.to_dict()


class TelemetryApiClient:
    def __init__(self, *, api_url: str, simulator_id: str) -> None:
        self.api_url = api_url.rstrip("/")
        self.simulator_id = simulator_id
        self.client = httpx.Client(timeout=30.0)

    def publish_batch(self, records: list[dict[str, object]]) -> dict[str, object]:
        if not records:
            return {"count": 0, "storage": "n/a"}

        payload = {
            "simulator_id": self.simulator_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "records": records,
        }
        response = self.client.post(f"{self.api_url}/telemetry", json=payload)
        response.raise_for_status()
        body = response.json()
        return {
            "count": body.get("processed_records", len(records)),
            "alerts": body.get("alerts", 0),
            "storage": body.get("storage", "unknown"),
        }

    def close(self) -> None:
        self.client.close()


def _next_vehicle_batch(vehicle_ids: list[str], cursor: int, batch_size: int) -> tuple[list[str], int]:
    if not vehicle_ids:
        return [], 0
    selected = [vehicle_ids[(cursor + index) % len(vehicle_ids)] for index in range(min(batch_size, len(vehicle_ids)))]
    next_cursor = (cursor + len(selected)) % len(vehicle_ids)
    return selected, next_cursor


def run_simulation(
    *,
    api_url: str,
    sleep_seconds: float,
    steps: int,
    batch_size: int,
    fleet_size: int,
    simulator_id: str,
) -> None:
    model_config = load_yaml(DEFAULT_MODEL_CONFIG)
    simulation_config = load_yaml(DEFAULT_SIMULATION_CONFIG)
    simulation_section = dict(simulation_config.get("simulation", {}))
    simulation_section["fleet_size"] = fleet_size
    simulation_config["simulation"] = simulation_section

    simulator = FleetSimulator(model_config=model_config, simulation_config=simulation_config)
    simulator.create_fleet()
    vehicle_ids = list(simulator.vehicles.keys())
    client = TelemetryApiClient(api_url=api_url, simulator_id=simulator_id)

    print(
        "[SIMULATOR] "
        f"fleet_size={len(vehicle_ids)} "
        f"batch_size={batch_size} "
        f"interval_ms={int(sleep_seconds * 1000)} "
        f"target={api_url}/telemetry"
    )

    step = 0
    cursor = 0
    next_deadline = time.perf_counter()

    try:
        while steps <= 0 or step < steps:
            step += 1
            batch_vehicle_ids, cursor = _next_vehicle_batch(vehicle_ids, cursor, batch_size)
            telemetry_batch = simulator.step_vehicle_batch(batch_vehicle_ids, dt_seconds=sleep_seconds)
            result = client.publish_batch(telemetry_batch)
            print(
                "[SIMULATOR] "
                f"step={step} "
                f"published={len(telemetry_batch)} "
                f"processed={result.get('count', '?')} "
                f"alerts={result.get('alerts', 0)} "
                f"storage={result.get('storage', 'unknown')}"
            )

            next_deadline += sleep_seconds
            remaining = next_deadline - time.perf_counter()
            if remaining > 0:
                time.sleep(remaining)
            else:
                next_deadline = time.perf_counter()
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the fleet simulator and post telemetry to FastAPI.")
    parser.add_argument(
        "--api-url",
        default=settings.simulator_api_url,
        help="FastAPI base URL that receives telemetry batches.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=max(0.05, settings.simulator_interval_ms / 1000.0),
        help="Delay between telemetry batches in seconds.",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=0,
        help="Number of batches to execute. Use 0 to run indefinitely.",
    )
    parser.add_argument(
        "--batch-size",
        "--vehicles-per-tick",
        type=int,
        default=settings.simulator_batch_size,
        help="How many vehicles to send in each telemetry batch.",
    )
    parser.add_argument(
        "--fleet-size",
        type=int,
        default=settings.simulator_fleet_size,
        help="How many vehicles to simulate.",
    )
    parser.add_argument(
        "--simulator-id",
        default=settings.simulator_id,
        help="Logical simulator shard identifier.",
    )
    args = parser.parse_args()
    run_simulation(
        api_url=args.api_url,
        sleep_seconds=max(0.05, args.sleep),
        steps=args.steps,
        batch_size=max(1, args.batch_size),
        fleet_size=max(1, args.fleet_size),
        simulator_id=args.simulator_id,
    )


if __name__ == "__main__":
    main()
