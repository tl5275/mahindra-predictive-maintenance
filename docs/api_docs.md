# API Documentation

Base URL: `http://localhost:8000`

## Fleet

### `GET /fleet?limit=100`
Returns a fleet snapshot for dashboard cards.

Response fields:
- `timestamp`
- `fleet_size`
- `vehicles[]` (telemetry + twin state)
- `fleet_health`

### `GET /vehicle/{vehicle_id}`
Returns telemetry, digital twin state, and latest diagnosis for one vehicle.

## Analytics

### `GET /fleet/health`
Returns:
- `fleet_size`
- `average_health_score`
- `status_counts` (`healthy`, `warning`, `critical`)
- `timestamp`

### `GET /fleet/failures`
Returns:
- `updated_at`
- `failure_summary`
- `diagnoses_count`
- `anomalies_count`
- `forecast`
- `schedule`
- `manufacturing_feedback`

## WebSocket

### `WS /ws/telemetry`
Streams periodic fleet snapshots:
- `timestamp`
- `fleet_size`
- `vehicles[]`

## Health Check

### `GET /healthz`
Readiness endpoint for local and container checks.
