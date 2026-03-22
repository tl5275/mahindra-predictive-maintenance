"""FastAPI backend serving Redis-backed fleet APIs and WebSocket relay."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.alerts_routes import router as alerts_router
from backend.api.fleet_routes import router as fleet_router
from backend.api.system_routes import router as system_router
from backend.api.telemetry_routes import router as telemetry_router
from backend.api.vehicle_routes import router as vehicle_router
from backend.core.config import get_settings
from backend.database.db import init_database
from backend.websocket.telemetry_stream import router as websocket_router, telemetry_broadcaster


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        init_database()
    except Exception:
        pass
    await telemetry_broadcaster.start()
    yield
    await telemetry_broadcaster.stop()


app = FastAPI(
    title="Mahindra Predictive Maintenance Platform",
    description="Local-first FastAPI, Redis, WebSocket and React fleet monitoring platform.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(telemetry_router)
app.include_router(fleet_router)
app.include_router(vehicle_router)
app.include_router(alerts_router)
app.include_router(websocket_router)


@app.get("/")
def root() -> dict:
    return {
        "service": "mahindra-backend",
        "version": app.version,
        "docs": "/docs",
        "telemetry_endpoint": "/telemetry",
        "fleet_endpoint": "/fleet",
        "vehicle_endpoint": "/vehicle/{vehicle_id}",
        "system_status": "/system-status",
        "metrics": "/metrics",
        "websocket": "/ws/fleet",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
