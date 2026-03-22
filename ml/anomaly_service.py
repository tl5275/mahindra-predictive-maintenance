"""Batch anomaly and RUL scoring service for optional offline/local model work."""

from __future__ import annotations

from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any

import numpy as np
from fastapi import FastAPI
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression

try:
    from ml.schemas import BatchPredictionRequest, BatchPredictionResponse
except ModuleNotFoundError:
    from schemas import BatchPredictionRequest, BatchPredictionResponse


ANOMALY_FEATURES = ("engine_temperature", "rpm", "battery_health", "vibration")
RUL_FEATURES = ("rpm", "engine_temperature", "battery_health", "vibration", "brake_wear", "odometer_km")
RANDOM_SEED = 42


class ModelBundle:
    """Owns lightweight models that can score telemetry batches quickly."""

    def __init__(self) -> None:
        self.random = np.random.default_rng(RANDOM_SEED)
        self.anomaly_model = self._train_isolation_forest()
        self.rul_model = self._train_rul_regressor()

    def _train_isolation_forest(self) -> IsolationForest:
        samples = 8000
        rpm = self.random.normal(2200, 650, samples).clip(700, 5200)
        temp = self.random.normal(96, 5.5, samples).clip(72, 120)
        battery = self.random.normal(88, 7.0, samples).clip(20, 100)
        vibration = (
            0.75
            + rpm / 2400
            + np.maximum(temp - 95, 0) * 0.035
            + np.maximum(80 - battery, 0) * 0.015
            + self.random.normal(0, 0.18, samples)
        ).clip(0.2, 6.5)

        model = IsolationForest(
            contamination=0.04,
            random_state=RANDOM_SEED,
            n_estimators=200,
        )
        model.fit(np.column_stack([temp, rpm, battery, vibration]))
        return model

    def _train_rul_regressor(self) -> LinearRegression:
        samples = 12000
        rpm = self.random.normal(2300, 760, samples).clip(650, 5600)
        temp = self.random.normal(97, 7.0, samples).clip(70, 135)
        battery = self.random.uniform(20, 100, samples)
        vibration = (
            0.85
            + rpm / 2350
            + np.maximum(temp - 95, 0) * 0.05
            + np.maximum(82 - battery, 0) * 0.02
            + self.random.normal(0, 0.22, samples)
        ).clip(0.2, 7.0)
        brake_wear = self.random.uniform(0, 100, samples)
        odometer_km = self.random.uniform(0, 240000, samples)

        rul = (
            2200
            - (odometer_km * 0.0068)
            - np.maximum(temp - 95, 0) * 7.5
            - np.maximum(vibration - 2.4, 0) * 105
            - np.maximum(72 - battery, 0) * 9.0
            - np.maximum(brake_wear - 45, 0) * 7.2
            - np.maximum(rpm - 3200, 0) * 0.08
            + self.random.normal(0, 45, samples)
        )
        rul = np.clip(rul, 8, 2400)

        model = LinearRegression()
        model.fit(
            np.column_stack([rpm, temp, battery, vibration, brake_wear, odometer_km]),
            rul,
        )
        return model

    def _anomaly_scores(self, records: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
        feature_matrix = np.array(
            [
                [
                    float(record.get("engine_temperature", 0.0)),
                    float(record.get("rpm", 0.0)),
                    float(record.get("battery_health", 0.0)),
                    float(record.get("vibration", 0.0)),
                ]
                for record in records
            ],
            dtype=float,
        )
        raw_scores = -self.anomaly_model.decision_function(feature_matrix)
        normalized = 1.0 / (1.0 + np.exp(-6.0 * (raw_scores - 0.18)))
        flags = self.anomaly_model.predict(feature_matrix) == -1
        return normalized, flags

    def _predict_component(self, record: dict[str, Any]) -> str:
        if float(record.get("battery_health", 100.0)) < 55:
            return "battery"
        if float(record.get("brake_wear", 0.0)) > 70:
            return "brakes"
        if float(record.get("engine_temperature", 0.0)) > 108 or float(record.get("vibration", 0.0)) > 3.6:
            return "engine"
        return "powertrain"

    def _health_status(self, health_score: float) -> str:
        if health_score < 40:
            return "critical"
        if health_score < 70:
            return "warning"
        return "healthy"

    def predict_batch(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not records:
            return []

        anomaly_scores, anomaly_flags = self._anomaly_scores(records)
        rul_features = np.array(
            [
                [
                    float(record.get("rpm", 0.0)),
                    float(record.get("engine_temperature", 0.0)),
                    float(record.get("battery_health", 0.0)),
                    float(record.get("vibration", 0.0)),
                    float(record.get("brake_wear", 0.0)),
                    float(record.get("odometer_km", 0.0)),
                ]
                for record in records
            ],
            dtype=float,
        )
        rul_predictions = np.clip(self.rul_model.predict(rul_features), 8, 2400)

        enriched: list[dict[str, Any]] = []
        for record, anomaly_score, anomaly_flag, rul_hours in zip(
            records,
            anomaly_scores,
            anomaly_flags,
            rul_predictions,
        ):
            anomaly_value = round(float(anomaly_score), 4)
            rul_value = int(round(float(rul_hours)))
            health_score = round(
                max(0.0, min(100.0, 100.0 - anomaly_value * 58.0 - max(0, 160 - rul_value) * 0.18)),
                2,
            )
            enriched.append(
                {
                    **record,
                    "anomaly_score": anomaly_value,
                    "anomaly_flag": bool(anomaly_flag or anomaly_value >= 0.8),
                    "rul_hours": rul_value,
                    "predicted_component": self._predict_component(record),
                    "health_score": health_score,
                    "health_status": self._health_status(health_score),
                }
            )
        return enriched


@lru_cache
def get_model_bundle() -> ModelBundle:
    return ModelBundle()


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_model_bundle()
    yield


app = FastAPI(
    title="Mahindra ML Service",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "models": {
            "anomaly": "IsolationForest",
            "rul": "LinearRegression",
            "anomaly_features": list(ANOMALY_FEATURES),
            "rul_features": list(RUL_FEATURES),
        },
    }


@app.post("/predict/batch", response_model=BatchPredictionResponse)
def predict_batch(payload: BatchPredictionRequest) -> BatchPredictionResponse:
    records = get_model_bundle().predict_batch(payload.records)
    return BatchPredictionResponse(records=records)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8010)
