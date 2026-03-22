"""Driving pattern primitives used by the fleet simulator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict
import random


@dataclass(frozen=True)
class DrivingProfile:
    """A lightweight profile describing how a vehicle behaves in a mode."""

    mode: str
    rpm_target: float
    speed_target_kmph: float
    temperature_bias: float
    oil_pressure_bias: float
    brake_wear_rate: float
    battery_drain_rate: float
    acceleration_factor: float


DRIVING_PROFILES: Dict[str, DrivingProfile] = {
    "idle": DrivingProfile(
        mode="idle",
        rpm_target=850,
        speed_target_kmph=0,
        temperature_bias=-4.0,
        oil_pressure_bias=3.5,
        brake_wear_rate=0.0015,
        battery_drain_rate=0.0010,
        acceleration_factor=0.05,
    ),
    "city": DrivingProfile(
        mode="city",
        rpm_target=1900,
        speed_target_kmph=38,
        temperature_bias=1.8,
        oil_pressure_bias=0.6,
        brake_wear_rate=0.028,
        battery_drain_rate=0.0030,
        acceleration_factor=0.22,
    ),
    "highway": DrivingProfile(
        mode="highway",
        rpm_target=2750,
        speed_target_kmph=88,
        temperature_bias=3.2,
        oil_pressure_bias=-0.5,
        brake_wear_rate=0.014,
        battery_drain_rate=0.0036,
        acceleration_factor=0.16,
    ),
    "heavy_load": DrivingProfile(
        mode="heavy_load",
        rpm_target=3200,
        speed_target_kmph=56,
        temperature_bias=8.5,
        oil_pressure_bias=-3.0,
        brake_wear_rate=0.046,
        battery_drain_rate=0.0062,
        acceleration_factor=0.12,
    ),
}

# Markov-like transition probabilities across modes.
MODE_TRANSITIONS: Dict[str, Dict[str, float]] = {
    "idle": {"idle": 0.60, "city": 0.33, "highway": 0.04, "heavy_load": 0.03},
    "city": {"idle": 0.18, "city": 0.58, "highway": 0.17, "heavy_load": 0.07},
    "highway": {"idle": 0.05, "city": 0.28, "highway": 0.60, "heavy_load": 0.07},
    "heavy_load": {"idle": 0.08, "city": 0.31, "highway": 0.11, "heavy_load": 0.50},
}


def select_next_mode(current_mode: str, rng: random.Random) -> str:
    """Draw the next driving mode from transition probabilities."""

    transitions = MODE_TRANSITIONS.get(current_mode, MODE_TRANSITIONS["city"])
    roll = rng.random()
    cumulative = 0.0
    for mode, probability in transitions.items():
        cumulative += probability
        if roll <= cumulative:
            return mode
    return "city"


def get_profile(mode: str) -> DrivingProfile:
    """Return a mode profile with a safe default for unknown mode names."""

    return DRIVING_PROFILES.get(mode, DRIVING_PROFILES["city"])
