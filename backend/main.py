"""FastAPI backend serving Redis-backed fleet APIs and WebSocket relay."""

from __future__ import annotations

import traceback
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from api.alerts_routes import router as alerts_router
    from api.fleet_routes import router as fleet_router
    from api.system_routes import router as system_router
    from api.telemetry_routes import router as telemetry_router
    from api.vehicle_routes import router as vehicle_router
    from core.config import get_settings
    from database.db import init_database
    from websocket.telemetry_stream import router as websocket_router, telemetry_broadcaster


    settings = get_settings()


    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            init_database()
        except Exception:
            print("STARTUP DB ERROR:")
            traceback.print_exc()
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
except Exception as error:
    print("STARTUP ERROR:")
    traceback.print_exc()
    raise error


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
