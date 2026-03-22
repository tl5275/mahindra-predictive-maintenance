"""Baseline Remaining Useful Life (RUL) regression model."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split


MODEL_PATH = Path(__file__).resolve().parent / "rul_model.pkl"
RANDOM_STATE = 42


def create_rul_dataset(size: int = 14000) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(RANDOM_STATE)
    rpm = rng.normal(2200, 820, size)
    engine_temp = rng.normal(98, 10, size)
    brake_wear = rng.uniform(0, 100, size)
    battery_health = rng.uniform(20, 100, size)
    odometer = rng.uniform(0, 150000, size)

    rul = (
        1400
        - (odometer * 0.006)
        - np.maximum(0, engine_temp - 98) * 2.2
        - np.maximum(0, brake_wear - 50) * 3.5
        - np.maximum(0, 70 - battery_health) * 2.0
        - np.maximum(0, rpm - 3200) * 0.15
        + rng.normal(0, 20, size)
    )
    rul = np.clip(rul, 0, 1500)

    x = np.column_stack([rpm, engine_temp, brake_wear, battery_health, odometer])
    return x, rul


def train_rul_model() -> GradientBoostingRegressor:
    x, y = create_rul_dataset()
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=RANDOM_STATE)

    model = GradientBoostingRegressor(
        random_state=RANDOM_STATE,
        n_estimators=220,
        learning_rate=0.06,
        max_depth=4,
    )
    model.fit(x_train, y_train)

    mae = mean_absolute_error(y_test, model.predict(x_test))
    print(f"RUL model MAE: {mae:.2f}")

    joblib.dump(model, MODEL_PATH)
    print(f"Saved RUL model to: {MODEL_PATH}")
    return model


if __name__ == "__main__":
    train_rul_model()
