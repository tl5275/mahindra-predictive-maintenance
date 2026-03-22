# System Design

## Runtime Design

- **Simulator**:
  - emits 100-vehicle telemetry batches every 200 ms by default
  - sends them directly to `POST /telemetry`
- **Backend Telemetry Pipeline**:
  - validates incoming batches
  - computes health score, anomaly score, predicted component, and RUL locally
  - evaluates alert rules
  - writes latest state to Redis when available, or in memory when Redis is down
  - writes telemetry history and maintenance artifacts to the database
  - broadcasts WebSocket deltas through `/ws/fleet`
- **Backend APIs**:
  - `GET /fleet`
  - `GET /vehicle/{id}`
  - `GET /alerts`
  - `GET /system-status`
  - `WebSocket /ws/fleet`
- **Frontend**:
  - initial snapshot via REST
  - live deltas via WebSocket
  - worker-driven filtering
  - list virtualization
  - map clustering

## Data Model

- **Latest Vehicle State**:
  - vehicle telemetry
  - anomaly score and flag
  - RUL estimate
  - health score and status
- **Database Tables**:
  - `telemetry_history`
  - `alert_records`
  - `maintenance_logs`

## Design Decisions

- Kafka was removed in favor of direct HTTP ingestion for stable localhost development.
- Redis is still used for hot-path state when available, but local fallback prevents the backend from becoming unusable during setup.
- The React frontend continues to avoid full-fleet re-renders by merging deltas into local state.
