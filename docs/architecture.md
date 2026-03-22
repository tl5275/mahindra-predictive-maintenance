# Architecture

## High-Level Pipeline

1. `simulator/fleet_simulator.py` advances a shard of synthetic Mahindra vehicles.
2. The simulator posts telemetry batches to `POST /telemetry`.
3. `backend/services/telemetry_pipeline.py` enriches records with health, anomaly, RUL, and alert metadata.
4. Latest fleet state is stored in Redis when available, with automatic in-memory fallback for local development.
5. Historical telemetry, alerts, and maintenance logs are persisted to SQLite/Postgres through SQLAlchemy.
6. `backend/websocket/telemetry_stream.py` broadcasts delta payloads to all active `/ws/fleet` clients.
7. `frontend/` hydrates from REST, listens to WebSocket deltas, virtualizes fleet lists, and clusters map markers.

## Module Boundaries

- Simulator: telemetry generation and HTTP delivery only.
- Backend telemetry pipeline: enrichment, alert creation, persistence, and latest-state updates.
- State layer: Redis-first latest-state storage with local memory fallback.
- Database: historical telemetry, alert, and maintenance persistence.
- WebSocket layer: active connection management and fleet delta fan-out.
- Frontend: React dashboard optimized for large fleet rendering without layout changes.

## Scalability Notes

- Redis remains the hot path for latest-state reads when available.
- WebSocket traffic carries delta payloads instead of full fleet snapshots.
- The frontend keeps a bounded working set and paginates the rendered fleet list.
- Simulator shards can be increased independently by running multiple simulator processes with different `SIMULATOR_ID` values.
