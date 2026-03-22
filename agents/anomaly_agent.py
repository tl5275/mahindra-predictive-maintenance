"""Statistical anomaly detection for streaming telemetry."""

from __future__ import annotations

from collections import defaultdict, deque
from statistics import mean, pstdev
from typing import Deque, DefaultDict, Dict, Iterable, List, Mapping


class AnomalyAgent:
    """Detect anomalies using rolling z-score checks per vehicle and metric."""

    def __init__(self, window_size: int = 30, z_threshold: float = 2.8) -> None:
        self.window_size = window_size
        self.z_threshold = z_threshold
        self.history: DefaultDict[str, Dict[str, Deque[float]]] = defaultdict(
            lambda: {
                "rpm": deque(maxlen=window_size),
                "engine_temperature": deque(maxlen=window_size),
                "oil_pressure": deque(maxlen=window_size),
                "brake_wear": deque(maxlen=window_size),
                "battery_health": deque(maxlen=window_size),
            }
        )

    def _z_score(self, series: Deque[float], value: float) -> float:
        if len(series) < 6:
            return 0.0
        std_dev = pstdev(series)
        if std_dev < 1e-6:
            return 0.0
        return abs((value - mean(series)) / std_dev)

    def detect(self, telemetry_batch: Iterable[Mapping[str, object]]) -> List[Dict[str, object]]:
        anomalies: List[Dict[str, object]] = []

        for telemetry in telemetry_batch:
            vehicle_id = str(telemetry["vehicle_id"])
            metric_history = self.history[vehicle_id]
            triggered_metrics: List[Dict[str, object]] = []

            for metric in metric_history.keys():
                value = float(telemetry[metric])
                z_value = self._z_score(metric_history[metric], value)
                if z_value >= self.z_threshold:
                    triggered_metrics.append(
                        {
                            "metric": metric,
                            "value": round(value, 2),
                            "z_score": round(z_value, 2),
                        }
                    )
                metric_history[metric].append(value)

            if triggered_metrics:
                anomalies.append(
                    {
                        "vehicle_id": vehicle_id,
                        "model": telemetry["model"],
                        "driving_mode": telemetry["driving_mode"],
                        "anomalies": triggered_metrics,
                    }
                )

        return anomalies
