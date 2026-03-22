"""Vehicle model with physics-inspired telemetry evolution."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
from typing import Dict, List, Mapping

from simulator.driving_patterns import DrivingProfile


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


@dataclass
class Vehicle:
    """Synthetic Mahindra vehicle state."""

    vehicle_id: str
    model: str
    rpm: float
    engine_temperature: float
    oil_pressure: float
    brake_wear: float
    battery_health: float
    speed_kmph: float = 0.0
    odometer_km: float = 0.0
    driving_mode: str = "city"
    active_failures: List[str] = field(default_factory=list)
    latitude: float = 20.0
    longitude: float = 78.0
    heading_deg: float = 0.0

    def step(
        self,
        dt_seconds: float,
        profile: DrivingProfile,
        model_spec: Mapping[str, float],
        failure_effects: Mapping[str, float],
        rng: random.Random,
    ) -> None:
        """Advance the vehicle state by one time step."""

        rpm_idle = float(model_spec.get("rpm_idle", 800))
        rpm_redline = float(model_spec.get("rpm_redline", 6000))
        nominal_temp = float(model_spec.get("engine_temp_nominal", 94))
        nominal_oil = float(model_spec.get("oil_pressure_nominal", 56))
        baseline_brake_wear = float(model_spec.get("brake_wear_rate", 0.02))

        rpm_multiplier = float(failure_effects.get("rpm_multiplier", 1.0))
        temp_bias = float(failure_effects.get("temp_bias", 0.0))
        oil_bias = float(failure_effects.get("oil_pressure_bias", 0.0))
        brake_bias = float(failure_effects.get("brake_wear_bias", 0.0))
        battery_multiplier = float(failure_effects.get("battery_drain_multiplier", 1.0))

        target_rpm = profile.rpm_target * rpm_multiplier + rng.gauss(0, 35)
        rpm_relaxation = 1.0 - math.exp(-0.45 * dt_seconds)
        self.rpm += (target_rpm - self.rpm) * rpm_relaxation
        self.rpm = _clamp(self.rpm, rpm_idle * 0.85, rpm_redline)

        target_speed = profile.speed_target_kmph * rpm_multiplier
        speed_relaxation = 1.0 - math.exp(-(0.08 + profile.acceleration_factor) * dt_seconds)
        self.speed_kmph += (target_speed - self.speed_kmph) * speed_relaxation
        self.speed_kmph = _clamp(self.speed_kmph, 0.0, 165.0)
        distance_km = self.speed_kmph * (dt_seconds / 3600.0)
        self.odometer_km += distance_km

        ambient_temp = 31.0
        thermal_equilibrium = (
            nominal_temp
            + profile.temperature_bias
            + 0.0015 * (self.rpm - rpm_idle)
            + 0.014 * self.speed_kmph
            + temp_bias
        )
        thermal_relaxation = 1.0 - math.exp(-0.22 * dt_seconds)
        self.engine_temperature += (thermal_equilibrium - self.engine_temperature) * thermal_relaxation
        self.engine_temperature += rng.gauss(0, 0.35)
        self.engine_temperature = _clamp(self.engine_temperature, ambient_temp, 145.0)

        oil_target = nominal_oil + profile.oil_pressure_bias - 0.004 * (self.rpm - rpm_idle) + oil_bias
        oil_relaxation = 1.0 - math.exp(-0.28 * dt_seconds)
        self.oil_pressure += (oil_target - self.oil_pressure) * oil_relaxation
        self.oil_pressure += rng.gauss(0, 0.12)
        self.oil_pressure = _clamp(self.oil_pressure, 12.0, 78.0)

        dynamic_brake_wear = (baseline_brake_wear + profile.brake_wear_rate + brake_bias) * dt_seconds
        if self.driving_mode == "city":
            dynamic_brake_wear *= 1.15
        self.brake_wear = _clamp(self.brake_wear + dynamic_brake_wear, 0.0, 100.0)

        temperature_stress = max(0.0, self.engine_temperature - nominal_temp) * 0.0008
        battery_drain = (profile.battery_drain_rate + temperature_stress) * battery_multiplier * dt_seconds
        self.battery_health = _clamp(self.battery_health - battery_drain, 0.0, 100.0)

        turn_std = 9.0 if self.driving_mode == "city" else 4.5 if self.driving_mode == "highway" else 6.5
        self.heading_deg = (self.heading_deg + rng.gauss(0, turn_std)) % 360.0
        heading_radians = math.radians(self.heading_deg)
        latitude_radians = math.radians(max(-89.0, min(89.0, self.latitude)))
        delta_lat = (distance_km / 111.0) * math.cos(heading_radians)
        delta_lon = (distance_km / (111.0 * max(0.2, math.cos(latitude_radians)))) * math.sin(heading_radians)
        self.latitude = _clamp(self.latitude + delta_lat, 8.0, 37.0)
        self.longitude = _clamp(self.longitude + delta_lon, 68.0, 97.0)

    def to_dict(self) -> Dict[str, float | str | List[str]]:
        """Return a serializable view used by telemetry and APIs."""

        return {
            "vehicle_id": self.vehicle_id,
            "model": self.model,
            "rpm": round(self.rpm, 2),
            "engine_temperature": round(self.engine_temperature, 2),
            "oil_pressure": round(self.oil_pressure, 2),
            "brake_wear": round(self.brake_wear, 2),
            "battery_health": round(self.battery_health, 2),
            "speed_kmph": round(self.speed_kmph, 2),
            "odometer_km": round(self.odometer_km, 2),
            "driving_mode": self.driving_mode,
            "active_failures": list(self.active_failures),
            "latitude": round(self.latitude, 6),
            "longitude": round(self.longitude, 6),
        }
