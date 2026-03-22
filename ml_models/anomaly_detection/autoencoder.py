"""Baseline anomaly model training (Isolation Forest placeholder)."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest


MODEL_PATH = Path(__file__).resolve().parent / "anomaly_model.pkl"
RANDOM_STATE = 42


def generate_training_data(size: int = 12000) -> np.ndarray:
    rng = np.random.default_rng(RANDOM_STATE)
    rpm = rng.normal(2100, 700, size)
    engine_temp = rng.normal(96, 8, size)
    oil_pressure = rng.normal(54, 6, size)
    brake_wear = rng.uniform(5, 70, size)
    battery_health = rng.uniform(55, 100, size)
    speed = rng.normal(48, 20, size)
    return np.column_stack([rpm, engine_temp, oil_pressure, brake_wear, battery_health, speed])


def train_anomaly_model() -> IsolationForest:
    x_train = generate_training_data()
    model = IsolationForest(
        n_estimators=200,
        contamination=0.03,
        random_state=RANDOM_STATE,
        n_jobs=1,
    )
    model.fit(x_train)
    joblib.dump(model, MODEL_PATH)
    print(f"Saved anomaly model to: {MODEL_PATH}")
    return model


if __name__ == "__main__":
    train_anomaly_model()
