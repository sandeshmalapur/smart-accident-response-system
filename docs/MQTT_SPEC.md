# MQTT Specification

Broker: Mosquitto (local dev via docker-compose, hosted broker in production)
QoS: 1 (at-least-once) for all topics — sensor data loss is unacceptable, occasional duplicates are tolerable
Retain: false on all topics (dashboard always wants live state, not stale retained messages)

---

## Topic Structure

Pattern: `safe/{device_code}/{stream}`

| Topic | Direction | Purpose |
|---|---|---|
| `safe/{device_code}/telemetry` | Publisher → Broker → Backend | Combined sensor reading (accel + gyro + gas + gps) |
| `safe/{device_code}/status` | Publisher → Broker → Backend | Device online/offline heartbeat |
| `ambulance/{ambulance_code}/location` | Publisher → Broker → Backend | Emergency ambulance continuous location stream (added Sprint 2) |

`{device_code}` matches `devices.device_code` in the database. `{ambulance_code}` matches `ambulances.ambulance_code` in the database. Backend resolves these codes on ingestion — if the code doesn't exist in the database, the message is rejected and logged.

---

## Payload: `safe/{device_code}/telemetry`

```json
{
  "device_code": "SIM-001",
  "recorded_at": "2026-08-06T10:15:30.123Z",
  "accel": { "x": 0.12, "y": -0.05, "z": 9.81 },
  "gyro": { "x": 0.01, "y": 0.02, "z": -0.01 },
  "gas_level": 120.5,
  "gps": { "lat": 12.9141, "lng": 74.8560 }
}
```

### Field Rules

| Field | Type | Required | Notes |
|---|---|---|---|
| device_code | string | yes | must match a registered device |
| recorded_at | ISO8601 string, UTC | yes | timestamp of measurement, not transmission |
| accel.x/y/z | float | yes | m/s², MPU6050-equivalent range |
| gyro.x/y/z | float | no | deg/s — nullable if simulator doesn't model rotation initially |
| gas_level | float | yes | MQ2-equivalent raw analog value (0–1023 simulated range) |
| gps.lat | float | yes | decimal degrees |
| gps.lng | float | yes | decimal degrees |

**This exact shape is the Phase 1 ↔ Phase 2 contract.** ESP32 firmware (Phase 11) must serialize to this identical JSON structure. No field renaming, no restructuring, no unit changes without a version bump and CHANGELOG entry.

---

## Payload: `ambulance/{ambulance_code}/location`

```json
{
  "ambulance_code": "AMB-001",
  "timestamp": "2026-08-13T23:30:00.000Z",
  "latitude": 12.9716,
  "longitude": 77.5946
}
```

### Field Rules

| Field | Type | Required | Notes |
|---|---|---|---|
| ambulance_code | string | yes | must match a registered ambulance |
| timestamp | ISO8601 string / ISO timestamp | yes | measurement timestamp |
| latitude | float | yes | decimal degrees |
| longitude | float | yes | decimal degrees |

---

## Payload: `safe/{device_code}/status`

```json
{
  "device_code": "SIM-001",
  "status": "online",
  "timestamp": "2026-08-06T10:15:00.000Z"
}
```

`status` values: `online`, `offline`. Published on connect/disconnect (LWT — Last Will and Testament — should be configured for `offline` on ungraceful disconnect, once we reach ESP32 phase).

---

## Publish Frequency
- `telemetry`: every 200ms–1s (configurable in simulator; matches realistic accelerometer sampling for accident detection)
- `ambulance location`: every 2–5s (ambulances do not require high-frequency 200ms telemetry)
- `status`: on connect, on disconnect, and every 30s heartbeat

---

## Backend Subscriber Behavior
1. Subscribe to `safe/+/telemetry`, `safe/+/status`, and `ambulance/+/location` (wildcard across devices/ambulances)
2. On `telemetry` message: validate schema → resolve `device_code` to `device_id` → persist to `sensor_readings` → pass to ML inference → broadcast via WebSocket
3. On `ambulance location` message: validate schema → resolve `ambulance_code` in DB → update `current_latitude`, `current_longitude`, and `last_location_update` timestamp. Drop and log unknown `ambulance_code`.
4. On `status` message: update device's last-seen state (in-memory or lightweight table)
5. Malformed payloads: log and drop, never crash the subscriber

---

## Versioning
If the payload schema must change in a breaking way, bump the topic to `safe/v2/{device_code}/telemetry` and support both during a migration window. Do not silently change the v1 shape.