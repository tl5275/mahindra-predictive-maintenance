"""Baseline failure prediction model training on synthetic telemetry data."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split


MODEL_PATH = Path(__file__).resolve().parent / "model.pkl"
RANDOM_STATE = 42


def build_synthetic_dataset(size: int = 14000) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(RANDOM_STATE)
    rpm = rng.normal(2200, 850, size)
    engine_temp = rng.normal(97, 12, size)
    oil_pressure = rng.normal(52, 9, size)
    brake_wear = rng.uniform(0, 100, size)
    battery_health = rng.uniform(20, 100, size)
    speed = rng.normal(45, 26, size)

    # Synthetic failure rule with stochastic noise.
    risk_score = (
        np.maximum(0, engine_temp - 102) * 0.35
        + np.maximum(0, 35 - oil_pressure) * 0.5
        + np.maximum(0, brake_wear - 74) * 0.22
        + np.maximum(0, 56 - battery_health) * 0.18
        + np.maximum(0, rpm - 4200) * 0.005
    )
    y = (risk_score + rng.normal(0, 2.5, size) > 12.5).astype(int)

    x = np.column_stack([rpm, engine_temp, oil_pressure, brake_wear, battery_health, speed])
    return x, y


def train_and_save_model() -> RandomForestClassifier:
    x, y = build_synthetic_dataset()
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=250,
        max_depth=12,
        random_state=RANDOM_STATE,
        n_jobs=1,
        class_weight="balanced_subsample",
    )
    model.fit(x_train, y_train)

    report = classification_report(y_test, model.predict(x_test), output_dict=False)
    print(report)

    joblib.dump(model, MODEL_PATH)
    print(f"Saved failure prediction model to: {MODEL_PATH}")
    return model


if __name__ == "__main__":
    train_and_save_model()
