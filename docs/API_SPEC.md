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

## Hospitals

### GET /hospitals
Query params: `is_active` (optional bool)
Response 200: array of hospital objects

### POST /hospitals
Auth: admin only
Request:
```json
{ "name": "string", "latitude": float, "longitude": float, "phone": "string" }
```
Response 201: created hospital object

### GET /hospitals/nearest
Query params: `lat` (float, required), `lng` (float, required), `limit` (int, default 3)
Response 200: array of nearest hospital objects, sorted by distance ascending:
```json
[
  {
    "id": "uuid",
    "name": "string",
    "latitude": 12.9716,
    "longitude": 77.5946,
    "phone": "+91 80 2345 6789",
    "is_active": true,
    "created_at": "2026-08-13T00:00:00Z",
    "distance_km": 1.24
  }
]
```

### GET /hospitals/{hospital_id}
Response 200: single hospital object
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
Response 200: array of incident objects (includes `nearest_hospital_id`), newest first

### GET /incidents/{incident_id}
Response 200: single incident object, including nested `sensor_reading`, `nearest_hospital`, and `alerts` array
Response 404: not found

### PATCH /incidents/{incident_id}
Request:
```json
{ "status": "acknowledged|resolved|false_positive" }
```
Response 200: updated incident object

> Note: incidents are NOT created via REST — they're created internally when ML inference flags a reading. For accident incidents, `nearest_hospital_id` is automatically populated during incident creation. PATCH is for operator triage only.

---

## Ambulances

### GET /ambulances
Query params: `status` (optional)
Response 200: array of ambulance objects

### POST /ambulances
Auth: admin only
Request:
```json
{ "ambulance_code": "AMB-001", "label": "Rapid Response Unit A" }
```
Response 201: created ambulance object

### GET /ambulances/nearest
Query params: `lat` (float, required), `lng` (float, required), `status` (default "available"), `limit` (default 3)
Response 200: array of nearest ambulance objects, sorted by distance ascending:
```json
[
  {
    "id": "uuid",
    "ambulance_code": "AMB-001",
    "label": "Rapid Response Unit A",
    "current_latitude": 12.9716,
    "current_longitude": 77.5946,
    "status": "available",
    "last_location_update": "2026-08-13T23:30:00Z",
    "created_at": "2026-08-13T00:00:00Z",
    "distance_km": 0.45
  }
]
```

### GET /ambulances/{ambulance_id_or_code}
Response 200: single ambulance object
Response 404: not found

---

## Dispatches

### POST /incidents/{incident_id}/dispatch
Auth: operator/admin
Request:
```json
{ "ambulance_id": "uuid" }
```
Response 201: created dispatch object (sets ambulance status to 'dispatched')
Response 400: ambulance not available or incident not found

### PATCH /dispatches/{dispatch_id}
Auth: operator/admin
Request:
```json
{ "status": "en_route|arrived|completed|cancelled" }
```
Response 200: updated dispatch object (updates ambulance status accordingly; 'completed' or 'cancelled' resets ambulance status back to 'available')

### GET /dispatches
Query params: `incident_id` (optional), `ambulance_id` (optional)
Response 200: array of dispatch objects, newest first

### GET /dispatches/{dispatch_id}
Response 200: single dispatch object

---

## Welfare Checks

### GET /welfare-checks/config/messages
Auth: none required
Response 200:
```json
{
  "prompt": "We detected a possible accident. Are you able to respond?",
  "safety_guidance": "Stay as still as possible. Do not attempt to move unless there is immediate danger (fire, traffic). Help is on the way.",
  "escalation_notice": "No response received. Emergency responders have been notified with elevated priority."
}
```

### POST /welfare-checks/{id}/respond
Auth: none required (occupant in-vehicle display)
Request:
```json
{ "response": "ok|help" }
```
Response 200: updated welfare_check object
Response 400: invalid response value or welfare check no longer awaiting response

### GET /welfare-checks/device/{device_code}
Auth: none required (in-vehicle display polling)
Response 200: active welfare check object for device

### GET /welfare-checks/{id}
Auth: none required
Response 200: single welfare check object with static message strings attached

### GET /welfare-checks
Auth: operator/admin
Query params: `incident_id` (optional), `device_id` (optional), `status` (optional)
Response 200: array of welfare check objects, newest first

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
{ "type": "welfare_check", "data": { ...welfare_check } }
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
All list endpoints: `limit` query param, results ordered newest-first.

## Versioning
All endpoints prefixed `/api/v1/`. Breaking changes require a new version prefix (`/api/v2/`), never a silent change to v1.
