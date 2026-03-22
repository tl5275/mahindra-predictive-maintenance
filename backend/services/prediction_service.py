"""AI failure prediction service for fleet telemetry."""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping

import numpy as np
from sklearn.ensemble import RandomForestClassifier


FEATURE_ORDER = [
    "rpm",
    "engine_temperature",
    "oil_pressure",
    "battery_health",
    "brake_wear",
]


class FailurePredictionService:
    """Train and serve a RandomForest-based failure risk model."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.model = self._train_model()

    def _generate_training_data(self, size: int = 18000) -> tuple[np.ndarray, np.ndarray]:
        rng = np.random.default_rng(self.seed)
        rpm = rng.normal(2200, 900, size)
        engine_temperature = rng.normal(96, 12, size)
        oil_pressure = rng.normal(52, 8, size)
        battery_health = rng.uniform(25, 100, size)
        brake_wear = rng.uniform(0, 100, size)

        # Base failure rule from requirement + additional degradation conditions.
        high_risk_rule = ((engine_temperature > 105) & (rpm > 2600)).astype(int)
        lubrication_risk = ((oil_pressure < 30) & (rpm > 2300)).astype(int)
        battery_risk = ((battery_health < 38) & (engine_temperature > 100)).astype(int)
        brake_risk = (brake_wear > 86).astype(int)

        noisy_risk_score = (
            high_risk_rule * 3
            + lubrication_risk * 2
            + battery_risk * 2
            + brake_risk * 2
            + (engine_temperature > 110).astype(int)
            + (rpm > 3200).astype(int)
            + rng.integers(0, 2, size)
        )
        y = (noisy_risk_score >= 3).astype(int)

        x = np.column_stack([rpm, engine_temperature, oil_pressure, battery_health, brake_wear])
        return x, y

    def _train_model(self) -> RandomForestClassifier:
        x, y = self._generate_training_data()
        model = RandomForestClassifier(
            n_estimators=220,
            max_depth=10,
            random_state=self.seed,
            n_jobs=-1,
            class_weight="balanced_subsample",
        )
        model.fit(x, y)
        model.n_jobs = 1
        return model

    def _predicted_component(self, telemetry: Mapping[str, object]) -> str:
        temp = float(telemetry.get("engine_temperature", 0.0))
        rpm = float(telemetry.get("rpm", 0.0))
        oil = float(telemetry.get("oil_pressure", 60.0))
        battery = float(telemetry.get("battery_health", 100.0))
        brake = float(telemetry.get("brake_wear", 0.0))

        component_scores = {
            "engine": max(0.0, (temp - 98.0) * 1.1 + (rpm - 2500.0) * 0.01),
            "lubrication": max(0.0, (35.0 - oil) * 2.0),
            "battery": max(0.0, (55.0 - battery) * 1.3),
            "brake": max(0.0, (brake - 70.0) * 1.2),
        }
        return max(component_scores, key=component_scores.get)

    def predict_vehicle(self, telemetry: Mapping[str, object]) -> Dict[str, object]:
        x = np.array([[float(telemetry.get(feature, 0.0)) for feature in FEATURE_ORDER]])
        failure_probability = float(self.model.predict_proba(x)[0][1])

        if failure_probability < 0.3:
            risk_level = "Low risk"
        elif failure_probability <= 0.6:
            risk_level = "Medium risk"
        else:
            risk_level = "High risk"

        return {
            "vehicle_id": str(telemetry.get("vehicle_id", "")),
            "failure_probability": round(failure_probability, 4),
            "risk_level": risk_level,
            "predicted_component": self._predicted_component(telemetry),
        }

    def predict_fleet(self, telemetry_batch: Iterable[Mapping[str, object]]) -> List[Dict[str, object]]:
        predictions = [self.predict_vehicle(item) for item in telemetry_batch]
        predictions.sort(key=lambda item: float(item["failure_probability"]), reverse=True)
        return predictions


prediction_service = FailurePredictionService()
