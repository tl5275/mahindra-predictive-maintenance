"""Direct telemetry ingestion routes used by the local simulator."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from backend.services.telemetry_pipeline import telemetry_pipeline
from backend.websocket.telemetry_stream import telemetry_broadcaster


router = APIRouter(tags=["Telemetry"])


@router.post("/telemetry")
async def ingest_telemetry(payload: Any = Body(...)) -> dict[str, Any]:
    try:
        records, alerts, state_result = telemetry_pipeline.process(payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    if state_result.payload:
        await telemetry_broadcaster.broadcast(state_result.payload)

    return {
        "status": "ok",
        "processed_records": len(records),
        "alerts": len(alerts),
        "storage": state_result.storage,
    }
