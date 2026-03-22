"""Synthetic failure injection for fleet telemetry."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import DefaultDict, Dict, Mapping
import random


@dataclass(frozen=True)
class FailureEffect:
    """Static effect knobs applied while a failure is active."""

    temp_bias: float = 0.0
    oil_pressure_bias: float = 0.0
    brake_wear_bias: float = 0.0
    battery_drain_multiplier: float = 1.0
    rpm_multiplier: float = 1.0
    sensor_noise_std: float = 0.0


FAILURE_EFFECTS: Dict[str, FailureEffect] = {
    "overheating": FailureEffect(temp_bias=13.0, oil_pressure_bias=-4.0, battery_drain_multiplier=1.15),
    "brake_failure": FailureEffect(brake_wear_bias=0.22, rpm_multiplier=0.95),
    "battery_degradation": FailureEffect(battery_drain_multiplier=2.8),
    "sensor_malfunction": FailureEffect(sensor_noise_std=42.0),
}


class FailureSimulator:
    """Injects persistent synthetic failures with condition-aware rates."""

    def __init__(self, failure_config: Mapping[str, float], seed: int = 99) -> None:
        self.random = random.Random(seed)
        self.failure_rates = {
            "overheating": float(failure_config.get("overheating_rate", 0.0008)),
            "brake_failure": float(failure_config.get("brake_failure_rate", 0.0007)),
            "battery_degradation": float(failure_config.get("battery_degradation_rate", 0.0006)),
            "sensor_malfunction": float(failure_config.get("sensor_malfunction_rate", 0.0004)),
        }
        self.active_failures: DefaultDict[str, Dict[str, int]] = defaultdict(dict)

    def _activate(self, vehicle_id: str, failure_name: str, ttl: int) -> None:
        if failure_name not in self.active_failures[vehicle_id]:
            self.active_failures[vehicle_id][failure_name] = ttl

    def _age_failures(self, vehicle_id: str) -> None:
        for failure_name in list(self.active_failures[vehicle_id].keys()):
            self.active_failures[vehicle_id][failure_name] -= 1
            if self.active_failures[vehicle_id][failure_name] <= 0:
                del self.active_failures[vehicle_id][failure_name]
        if not self.active_failures[vehicle_id]:
            del self.active_failures[vehicle_id]

    def _effective_rate(self, failure_name: str, vehicle_state: Mapping[str, float | str]) -> float:
        rate = self.failure_rates[failure_name]
        if failure_name == "overheating":
            if float(vehicle_state["engine_temperature"]) > 104:
                rate *= 2.4
            if float(vehicle_state["rpm"]) > 4200:
                rate *= 1.8
        elif failure_name == "brake_failure":
            if float(vehicle_state["brake_wear"]) > 70:
                rate *= 2.6
        elif failure_name == "battery_degradation":
            if float(vehicle_state["battery_health"]) < 62:
                rate *= 2.2
        elif failure_name == "sensor_malfunction":
            if float(vehicle_state["odometer_km"]) > 35000:
                rate *= 1.6
        return rate

    def step_vehicle(self, vehicle_state: Mapping[str, float | str]) -> Dict[str, object]:
        """Update failure states and return active failures plus aggregate effects."""

        vehicle_id = str(vehicle_state["vehicle_id"])
        self._age_failures(vehicle_id)

        for failure_name in self.failure_rates:
            if failure_name in self.active_failures.get(vehicle_id, {}):
                continue
            rate = self._effective_rate(failure_name, vehicle_state)
            if self.random.random() < rate:
                ttl = self.random.randint(25, 140)
                self._activate(vehicle_id, failure_name, ttl)

        active = list(self.active_failures.get(vehicle_id, {}).keys())
        combined = {
            "temp_bias": 0.0,
            "oil_pressure_bias": 0.0,
            "brake_wear_bias": 0.0,
            "battery_drain_multiplier": 1.0,
            "rpm_multiplier": 1.0,
            "sensor_noise_std": 0.0,
        }
        for failure_name in active:
            effect = FAILURE_EFFECTS[failure_name]
            combined["temp_bias"] += effect.temp_bias
            combined["oil_pressure_bias"] += effect.oil_pressure_bias
            combined["brake_wear_bias"] += effect.brake_wear_bias
            combined["battery_drain_multiplier"] *= effect.battery_drain_multiplier
            combined["rpm_multiplier"] *= effect.rpm_multiplier
            combined["sensor_noise_std"] += effect.sensor_noise_std

        return {"active_failures": active, "effects": combined}
