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

## Key Constraint
Swapping the Simulator for ESP32 must require **zero backend code changes** — only the publisher changes, MQTT schema stays identical.