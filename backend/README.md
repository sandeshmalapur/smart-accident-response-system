# Backend — Smart Accident Response System

FastAPI backend implementing auth, DB models, MQTT subscriber, WebSocket
broadcaster, and REST endpoints per `API_SPEC.md`, `DATABASE_SCHEMA.md`,
and `MQTT_SPEC.md` (all frozen contracts — see `PROJECT_CONSTITUTION.md`).

## Setup

```bash
cd backend
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit if your docker-compose ports differ
```

Start local infra (from repo root, where docker-compose.yml lives):

```bash
docker compose up -d postgres mosquitto
```

Run migrations, then seed a test user + device:

```bash
alembic upgrade head
python -m scripts.seed
```

Run the app:

```bash
uvicorn app.main:app --reload
```

## Verification checklist

- `uvicorn app.main:app --reload` → starts, `GET /health` returns `{"status": "ok"}`
- `alembic upgrade head` → creates `users`, `devices`, `sensor_readings`, `incidents`, `alerts`
- `POST /api/v1/auth/login` with `admin@example.com` / `changeme123` (from seed script) → returns a JWT
- `GET /api/v1/devices`, `/readings`, `/incidents`, `/alerts` (with `Authorization: Bearer <token>`) → 200, empty arrays pre-data
- MQTT subscriber connects to Mosquitto on startup (check logs for "MQTT connected")
- Publish a test telemetry message (device `SIM-001` is seeded):

```bash
mosquitto_pub -h localhost -t safe/SIM-001/telemetry -q 1 -m '{
  "device_code": "SIM-001",
  "recorded_at": "2026-08-06T10:15:30.123Z",
  "accel": {"x": 0.12, "y": -0.05, "z": 9.81},
  "gyro": {"x": 0.01, "y": 0.02, "z": -0.01},
  "gas_level": 120.5,
  "gps": {"lat": 12.9141, "lng": 74.8560}
}'
```

  → a new row appears in `sensor_readings` (check logs, or `GET /api/v1/readings/latest`)

- Connect to `ws://localhost:8000/api/v1/ws/live?token=<JWT>` (e.g. with `websocat` or a browser) and publish the message above again → observe a `{"type": "reading", "data": {...}}` broadcast

## Tests

```bash
pytest -v
```

`test_security.py` and `test_mqtt_validation.py` are pure unit tests (no DB
needed). `test_auth_api.py` and `test_mqtt_integration.py` need Postgres up
and migrated (`docker compose up -d postgres && alembic upgrade head`).

## Notes / deviations flagged during implementation

1. Added `app/schemas/` (Pydantic request/response models) and
   `app/services/` (business logic, per the "thin controllers" coding
   standard) as subfolders under `app/` — additive, not a change to the
   frozen folder structure outside `backend/`.
2. Device online/offline state from `safe/{device_code}/status` is kept
   **in-memory** on the MQTT subscriber rather than a new DB table, per
   `MQTT_SPEC.md`'s own suggestion ("in-memory or lightweight table — not
   yet in `DATABASE_SCHEMA.md`, add if needed"). The 5-table schema stays
   frozen. Revisit if the dashboard needs this persisted/queryable.
3. `WS /ws/live` is mounted at `/api/v1/ws/live`. `API_SPEC.md` states the
   Base URL is `/api/v1` and lists every other endpoint relative to it; the
   WS entry is listed the same way, so it's mounted under the same prefix
   for consistency. Flagging in case the intent was actually an
   unversioned `/ws/live`.
4. ML inference (`app/ml/inference.py`) and alert dispatch
   (`app/services/alert_service.py`) are stubs per the sprint scope —
   inference always returns "not an incident" with placeholder scores, so
   no incidents/alerts will be created against real MQTT data yet. This
   is intentional; Sprint S3 wires in real SVM/GMM models.
