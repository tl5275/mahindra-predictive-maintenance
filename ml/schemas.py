"""ML service-local API schemas to keep the service independent from backend code."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class BatchPredictionRequest(BaseModel):
    records: list[dict[str, Any]]


class BatchPredictionResponse(BaseModel):
    records: list[dict[str, Any]]
