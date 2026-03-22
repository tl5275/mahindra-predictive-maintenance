"""Telemetry serialization layer between simulator and backend services."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Iterable, List, Mapping, Optional
import random


class TelemetryGenerator:
    """Builds telemetry records from vehicle states and failure effects."""

    def __init__(self, seed: int = 123) -> None:
        self.random = random.Random(seed)

    def _sensorized_value(self, value: float, sensor_noise_std: float) -> float:
        if sensor_noise_std <= 0:
            return value
        return value + self.random.gauss(0, sensor_noise_std)

    def _derive_vibration(
        self,
        *,
        rpm: float,
        engine_temperature: float,
        brake_wear: float,
        battery_health: float,
        active_failures: list[str],
        sensor_noise_std: float,
    ) -> float:
        vibration = (
            0.35
            + rpm / 2500.0
            + max(0.0, engine_temperature - 95.0) * 0.045
            + brake_wear * 0.008
            + max(0.0, 80.0 - battery_health) * 0.01
            + len(active_failures) * 0.25
        )
        return self._sensorized_value(vibration, max(0.03, sensor_noise_std * 0.01))

    def generate_record(
        self,
        vehicle_state: Mapping[str, object],
        failure_effects: Mapping[str, float],
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, object]:
        """Create one telemetry event suitable for downstream processing."""

        event_time = timestamp or datetime.now(timezone.utc)
        sensor_noise_std = float(failure_effects.get("sensor_noise_std", 0.0))

        rpm = self._sensorized_value(float(vehicle_state["rpm"]), sensor_noise_std * 0.75)
        engine_temperature = self._sensorized_value(
            float(vehicle_state["engine_temperature"]), sensor_noise_std * 0.03
        )
        oil_pressure = self._sensorized_value(float(vehicle_state["oil_pressure"]), sensor_noise_std * 0.02)
        brake_wear = self._sensorized_value(float(vehicle_state["brake_wear"]), sensor_noise_std * 0.01)
        battery_health = self._sensorized_value(float(vehicle_state["battery_health"]), sensor_noise_std * 0.01)
        active_failures = list(vehicle_state["active_failures"])
        vibration = self._derive_vibration(
            rpm=rpm,
            engine_temperature=engine_temperature,
            brake_wear=brake_wear,
            battery_health=battery_health,
            active_failures=active_failures,
            sensor_noise_std=sensor_noise_std,
        )

        return {
            "timestamp": event_time.isoformat(),
            "vehicle_id": vehicle_state["vehicle_id"],
            "model": vehicle_state["model"],
            "driving_mode": vehicle_state["driving_mode"],
            "rpm": round(max(0.0, rpm), 2),
            "engine_temperature": round(max(0.0, engine_temperature), 2),
            "oil_pressure": round(max(0.0, oil_pressure), 2),
            "brake_wear": round(max(0.0, brake_wear), 2),
            "battery_health": round(max(0.0, battery_health), 2),
            "vibration": round(max(0.0, vibration), 3),
            "speed_kmph": vehicle_state["speed_kmph"],
            "odometer_km": vehicle_state["odometer_km"],
            "active_failures": active_failures,
            "latitude": vehicle_state["latitude"],
            "longitude": vehicle_state["longitude"],
        }

    def generate_batch(
        self,
        vehicle_states: Iterable[Mapping[str, object]],
        effects_by_vehicle: Mapping[str, Mapping[str, float]],
        timestamp: Optional[datetime] = None,
    ) -> List[Dict[str, object]]:
        """Create telemetry records for a fleet state snapshot."""

        return [
            self.generate_record(
                vehicle_state=state,
                failure_effects=effects_by_vehicle.get(str(state["vehicle_id"]), {}),
                timestamp=timestamp,
            )
            for state in vehicle_states
        ]
