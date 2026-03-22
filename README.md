# Mahindra Predictive Maintenance Platform

Local-first predictive maintenance platform built around a direct telemetry path:

`Simulator -> FastAPI (/telemetry) -> Redis or in-memory state -> WebSocket -> React`

## What Changed

- Kafka and Zookeeper were removed.
- The simulator now posts directly to `POST /telemetry`.
- The backend processes telemetry locally, stores latest vehicle state, and broadcasts deltas over `/ws/fleet`.
- The frontend reads its API base URL from `import.meta.env.VITE_API_URL`.
- Local persistence defaults to SQLite at `data/mahindra_local.db`.

## Local Run

Install dependencies once:

```bash
pip install -r requirements.txt
cd frontend
npm install
cd ..
```

Run the three local processes in separate terminals:

```bash
uvicorn backend.main:app --reload
```

```bash
cd frontend
npm run dev
```

```bash
python simulator/fleet_simulator.py
```

If you want Redis-backed latest state, run Redis locally on `localhost:6379`. If Redis is not available, the backend falls back to in-memory state so local development still works.

## Important Endpoints

- `POST /telemetry`
- `GET /health`
- `GET /system-status`
- `GET /fleet`
- `GET /vehicle/{vehicle_id}`
- `GET /alerts`
- `WebSocket /ws/fleet`

## Environment

Root `.env` defaults:

```env
API_PORT=8000
REDIS_URL=redis://localhost:6379
DATABASE_URL=sqlite:///data/mahindra_local.db
SIMULATOR_API_URL=http://localhost:8000
VITE_API_URL=http://localhost:8000
```

`frontend/vite.config.js` reads the root `.env`, so `npm run dev` will use `VITE_API_URL` automatically.

## Docker

The compose files were simplified to `redis + backend + simulator + frontend`:

```bash
python run_platform.py up
```

or:

```bash
docker compose up --build
```

## Validation Checklist

After startup, verify:

1. `http://localhost:8000/health` is reachable.
2. `http://localhost:8000/system-status` shows growing `total_batches` and `total_records`.
3. `http://localhost:8000/fleet` returns live vehicle state.
4. `ws://localhost:8000/ws/fleet` receives delta messages.
5. The frontend updates live while the simulator is running.

## Git Push Scripts

Manual prompt:

```powershell
.\scripts\git_push.ps1
```

Automatic commit message:

```powershell
.\scripts\git_auto_push.ps1
```
