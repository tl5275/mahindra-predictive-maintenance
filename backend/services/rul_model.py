"""Remaining Useful Life prediction service."""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping

import numpy as np
from sklearn.ensemble import RandomForestRegressor


FEATURE_ORDER = [
    "rpm",
    "engine_temperature",
    "oil_pressure",
    "battery_health",
    "brake_wear",
    "vehicle_health_score",
]


class RULPredictionService:
    """Trains and serves a RandomForestRegressor for RUL estimation."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.model = self._train_model()

    def _generate_training_data(self, size: int = 22000) -> tuple[np.ndarray, np.ndarray]:
        rng = np.random.default_rng(self.seed)
        rpm = rng.normal(2200, 950, size)
        engine_temperature = rng.normal(98, 12, size)
        oil_pressure = rng.normal(52, 8, size)
        battery_health = rng.uniform(20, 100, size)
        brake_wear = rng.uniform(0, 100, size)
        vehicle_health_score = rng.uniform(25, 100, size)

        # Synthetic degradation law for remaining hours before failure.
        remaining_hours = (
            520
            - np.maximum(0, rpm - 1700) * 0.035
            - np.maximum(0, engine_temperature - 95) * 4.6
            - np.maximum(0, 38 - oil_pressure) * 6.0
            - np.maximum(0, 70 - battery_health) * 2.2
            - np.maximum(0, brake_wear - 45) * 3.0
            - np.maximum(0, 82 - vehicle_health_score) * 3.4
            + rng.normal(0, 18, size)
        )
        remaining_hours = np.clip(remaining_hours, 1, 720)

        x = np.column_stack([rpm, engine_temperature, oil_pressure, battery_health, brake_wear, vehicle_health_score])
        return x, remaining_hours

    def _train_model(self) -> RandomForestRegressor:
        x, y = self._generate_training_data()
        model = RandomForestRegressor(
            n_estimators=240,
            max_depth=12,
            random_state=self.seed,
            n_jobs=-1,
        )
        model.fit(x, y)
        model.n_jobs = 1
        return model

    def _estimate_confidence(self, x: np.ndarray) -> float:
        # Confidence derived from ensemble disagreement (lower std => higher confidence).
        tree_preds = np.array([tree.predict(x)[0] for tree in self.model.estimators_])
        std = float(np.std(tree_preds))
        confidence = 1.0 - min(1.0, std / 250.0)
        return round(max(0.55, min(0.99, confidence)), 3)

    def predict_vehicle(
        self,
        telemetry: Mapping[str, object],
        predicted_component: str = "engine",
    ) -> Dict[str, object]:
        x = np.array(
            [[float(telemetry.get(feature, 0.0)) for feature in FEATURE_ORDER]],
            dtype=float,
        )
        rul_hours = float(self.model.predict(x)[0])
        rul_hours = float(max(1.0, min(720.0, rul_hours)))

        return {
            "vehicle_id": str(telemetry.get("vehicle_id", "")),
            "predicted_component": predicted_component,
            "remaining_useful_life_hours": int(round(rul_hours)),
            "confidence": self._estimate_confidence(x),
        }

    def predict_fleet(self, telemetry_batch: Iterable[Mapping[str, object]]) -> List[Dict[str, object]]:
        predictions = [self.predict_vehicle(item, str(item.get("predicted_component", "engine"))) for item in telemetry_batch]
        predictions.sort(key=lambda item: int(item["remaining_useful_life_hours"]))
        return predictions


rul_model_service = RULPredictionService()
