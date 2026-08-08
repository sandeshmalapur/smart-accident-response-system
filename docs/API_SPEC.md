# API Specification

Base URL: `/api/v1`
Auth: JWT Bearer token (except `/auth/login`)
Content-Type: `application/json`

---

## Auth

### POST /auth/login
Request:
```json
{ "email": "string", "password": "string" }
```
Response 200:
```json
{ "access_token": "string", "token_type": "bearer", "user": { "id": "uuid", "email": "string", "full_name": "string", "role": "string" } }
```
Response 401: invalid credentials

### GET /auth/me
Response 200: current user object (as above, without token)

---

## Devices

### GET /devices
Query params: `is_active` (optional bool)
Response 200: array of device objects

### POST /devices
Auth: admin only
Request:
```json
{ "device_code": "string", "device_type": "simulator|esp32", "label": "string" }
```
Response 201: created device object

### GET /devices/{device_id}
Response 200: single device object
Response 404: not found

---

## Sensor Readings

### GET /readings
Query params: `device_id` (optional), `from` (ISO datetime), `to` (ISO datetime), `limit` (default 100, max 1000)
Response 200: array of sensor_reading objects, newest first

### GET /readings/latest
Query params: `device_id` (optional — if omitted, latest per device)
Response 200: array of most recent reading per device

> Note: readings are NOT created via REST — they arrive via MQTT ingestion only. This endpoint is read-only.

---

## Incidents

### GET /incidents
Query params: `status` (optional), `incident_type` (optional), `device_id` (optional), `sensor_reading_id` (optional), `from`, `to`, `limit` (default 50)
Response 200: array of incident objects, newest first

### GET /incidents/{incident_id}
Response 200: single incident object, including nested `sensor_reading` and `alerts` array
Response 404: not found

### PATCH /incidents/{incident_id}
Request:
```json
{ "status": "acknowledged|resolved|false_positive" }
```
Response 200: updated incident object

> Note: incidents are NOT created via REST — they're created internally when ML inference flags a reading. PATCH is for operator triage only.

---

## Alerts

### GET /alerts
Query params: `incident_id` (optional), `limit` (default 50)
Response 200: array of alert objects, newest first

---

## WebSocket

### WS /ws/live
Auth: JWT passed as query param `?token=...` on connection
Server → Client messages:
```json
{ "type": "reading", "data": { ...sensor_reading } }
{ "type": "incident", "data": { ...incident } }
{ "type": "alert", "data": { ...alert } }
```
No client → server messages expected (broadcast-only channel in Phase 1).

---

## Standard Error Shape
```json
{ "detail": "human-readable error message" }
```

## Standard Status Codes
- 200 — success
- 201 — created
- 400 — validation error
- 401 — unauthenticated
- 403 — unauthorized (role check failed)
- 404 — not found
- 422 — malformed request body

## Pagination Convention
All list endpoints: `limit` query param, results ordered newest-first. Cursor/offset pagination deferred — not needed at Phase 1 data volumes.

## Versioning
All endpoints prefixed `/api/v1/`. Breaking changes require a new version prefix (`/api/v2/`), never a silent change to v1.