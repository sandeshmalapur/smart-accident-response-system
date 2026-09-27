# Architecture

## System Diagram

[ESP32 / Simulator] --MQTT--> [Mosquitto Broker] --> [FastAPI MQTT Subscriber]
|
v
[Ingestion Service]
/
[ML Inference] [PostgreSQL]
(SVM + GMM) (Supabase) 
\ /
v v
[WebSocket Broadcaster]
|
v
[React Dashboard]


## Components

### Simulator / ESP32 (Publisher)
Publishes sensor readings (accelerometer, gas, GPS) to MQTT topics on a fixed schema. Both must be interchangeable — see MQTT_SPEC.md (next doc, Phase 5).

### Mosquitto Broker
Local dev broker (via docker-compose). Handles pub/sub between publisher and backend.

### FastAPI Backend
- **MQTT Subscriber**: listens to sensor topics, validates payload, hands off to ingestion.
- **Ingestion Service**: persists raw readings, triggers ML inference.
- **ML Inference**: loads joblib SVM (severity) + GMM (anomaly) models, scores incoming data.
- **Alert Module**: mock notification dispatch (extensible interface for real SMS/email later).
- **WebSocket Broadcaster**: pushes live state (readings, severity, alerts) to connected dashboard clients.
- **REST API (`/api/v1/`)**: auth, historical queries, incident CRUD.

## ML Inference — Design Decisions (frozen, Sprint S3)

**Return shape:** `run_inference()` returns `list[InferenceResult]`, not a single
`InferenceResult`. Length is 0, 1, or 2:
- 0 — neither model fires, no incident
- 1 — either the SVM (severity ≠ minor) or the GMM (gas anomaly) fires, not both
- 2 — both fire on the same reading (e.g. severe crash + simultaneous gas leak)

This is a direct consequence of `DATABASE_SCHEMA.md`'s `incidents.incident_type`
being a single-value enum (`accident` XOR `gas_leak`, not both) — a reading can't
be represented as one incident row if it trips both models, so it becomes two rows
sharing the same `sensor_reading_id` (that FK is not unique-constrained).

The MQTT pipeline (`backend/app/mqtt/client.py`) loops over this list, creating
zero, one, or two incidents/alerts/broadcasts per reading accordingly.

**Co-occurrence Note:** The GMM anomaly detector is a joint multivariate model over `[gas_level_norm, accel_magnitude]`, not a gas-level-only detector (per PROJECT_CONSTITUTION.md #4). A severe accident (large accel spike) can independently trigger the GMM even with normal gas_level. Consumers of `incidents` (frontend, alerts) MUST check for a sibling incident sharing the same `sensor_reading_id` before presenting a `gas_leak` incident as a standalone gas leak — displaying it as "gas anomaly detected during accident" when a sibling `accident` incident exists.


**Any future change to this return shape (e.g. collapsing to a single result, or
changing to some other multi-result structure) must update all three of:
`backend/app/ml/inference.py`, `backend/app/mqtt/client.py`, and this doc — in the
same change.**

**Model code location:** `backend/app/ml/` holds a **self-contained copy** of the
inference logic and trained models (`features.py`, `_inference_service.py`,
`models/*.joblib`), synced from the repo-root `ml/` training track via
`backend/app/ml/sync_models.py`. Backend does NOT import across the repo boundary
into root `ml/` at runtime — this keeps `backend/` independently buildable/
deployable (e.g. as its own Docker image) without requiring the rest of the
monorepo to be present. Root `ml/` remains the source of truth for training;
`backend/app/ml/` is a frozen runtime snapshot, re-synced by hand after retraining.
See `backend/app/ml/README.md` for the sync procedure.

### PostgreSQL (Supabase in prod, Docker Postgres in local dev)
Stores: raw sensor readings, incidents, severity scores, alert logs, user accounts.

### React Dashboard
- Live view (WebSocket-driven)
- Historical view (REST-driven)
- Alerts panel

## Environments

| Environment | Postgres | MQTT Broker |
|---|---|---|
| Local Dev | Docker (docker-compose) | Docker Mosquitto |
| Production | Supabase | Hosted/self-managed Mosquitto |

## Data Flow Contract
1. Publisher → MQTT topic (fixed schema, see MQTT_SPEC.md)
2. Backend subscribes → validates → persists raw reading
3. ML inference scores severity/anomaly → persists result
4. If severity/anomaly crosses threshold → Alert Module triggers (mocked in Phase 1)
5. WebSocket broadcasts updated state to all connected dashboards
6. Dashboard renders live + historical views via WS + REST respectively

3. **Twilio SMS Alert & Public Relative Tracking (Sprint 4)**:
   - When a severe accident incident is flagged and the registered device has an emergency contact phone number, the backend generates a 24-hour cryptographically secure random tracking token (`IncidentTrackingToken`).
   - `sms_service.py` dispatches an SMS containing a direct public tracking link (`http://<host>/track/<token>`).
   - **Twilio Trial Account Limitation Note**: The implementation uses Twilio. In trial mode, SMS alerts can only be delivered to phone numbers that are explicitly verified in the Twilio console. Unconfigured credentials or unverified numbers trigger a graceful warning without crashing the backend service.
   - **Public Tracking Endpoint (`GET /api/v1/track/{token}`)**: Intentionally unauthenticated endpoint allowing emergency contacts without dashboard user accounts to track live incident status, nearest hospital info, and live ambulance position on a clean, calming mobile interface.

## Key Constraints & Safety Rules


1. **Swapping the Simulator for ESP32**: Must require **zero backend code changes** — only the publisher changes, MQTT schema stays identical.
2. **Victim Welfare Check & Static Safety Guidance (Permanent Architectural Rule)**:
   This system **NEVER** generates dynamic medical advice or AI-composed text shown to vehicle occupants. All strings rendered on the in-vehicle welfare check screen (`/vehicle/:deviceCode`) are strictly fixed, pre-reviewed static constants configured once in `backend/app/core/welfare_messages.py` (`WELFARE_CHECK_PROMPT`, `SAFETY_GUIDANCE`, `ESCALATION_NOTICE`). The system's sole functions during post-crash welfare check are:
   - Prompting the occupant if they are able to respond.
   - Presenting binary touch buttons (`"I'M OK"` / `"I NEED HELP"`).
   - Displaying generic, universally safe static guidance ("stay still, help is on the way").
   - Automatically escalating urgency to the operator dashboard if no response is received within 90 seconds.
   No free-text input, open-ended chat, or dynamic AI generation is permitted anywhere in this pipeline.