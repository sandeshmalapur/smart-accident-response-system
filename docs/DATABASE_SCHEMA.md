# Database Schema

## Engine
PostgreSQL (Supabase in production, Docker Postgres in local dev). Managed via SQLAlchemy models + Alembic migrations.

---

## Tables

### 1. `users`
Operators/admins who log into the dashboard. No public signup — accounts provisioned manually or via seed script.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK, default gen_random_uuid() |
| email | VARCHAR(255) | UNIQUE, NOT NULL |
| hashed_password | VARCHAR(255) | NOT NULL |
| full_name | VARCHAR(255) | NOT NULL |
| role | VARCHAR(50) | NOT NULL, default 'operator' (values: admin, operator) |
| is_active | BOOLEAN | NOT NULL, default true |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |

---

### 2. `devices`
Represents a simulator instance or a physical ESP32 unit. Needed so readings/incidents can be traced to a source.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK, default gen_random_uuid() |
| device_code | VARCHAR(100) | UNIQUE, NOT NULL (e.g. "SIM-001", "ESP32-004") |
| device_type | VARCHAR(50) | NOT NULL (values: simulator, esp32) |
| label | VARCHAR(255) | nullable (human-readable name, e.g. "Test Vehicle A") |
| is_active | BOOLEAN | NOT NULL, default true |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |

---

### 3. `sensor_readings`
Raw ingested data from MQTT — one row per message received.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK, default gen_random_uuid() |
| device_id | UUID | FK → devices.id, NOT NULL |
| accel_x | FLOAT | NOT NULL |
| accel_y | FLOAT | NOT NULL |
| accel_z | FLOAT | NOT NULL |
| gyro_x | FLOAT | nullable |
| gyro_y | FLOAT | nullable |
| gyro_z | FLOAT | nullable |
| gas_level | FLOAT | NOT NULL (MQ2 reading) |
| latitude | FLOAT | NOT NULL |
| longitude | FLOAT | NOT NULL |
| recorded_at | TIMESTAMPTZ | NOT NULL (timestamp from device) |
| received_at | TIMESTAMPTZ | NOT NULL, default now() (server ingestion time) |

Index: `(device_id, recorded_at)` for time-series queries.

---

### 4. `hospitals`
Static hospital registry for auto-suggested nearest hospital emergency response (added Sprint 1).

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK, default gen_random_uuid() |
| name | VARCHAR(255) | NOT NULL |
| latitude | FLOAT | NOT NULL |
| longitude | FLOAT | NOT NULL |
| phone | VARCHAR(50) | nullable |
| is_active | BOOLEAN | NOT NULL, default true |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |

---

### 5. `incidents`
Created when ML inference flags a reading as accident/anomaly above threshold.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK, default gen_random_uuid() |
| device_id | UUID | FK → devices.id, NOT NULL |
| sensor_reading_id | UUID | FK → sensor_readings.id, NOT NULL |
| nearest_hospital_id | UUID | FK → hospitals.id, nullable (auto-suggested on accident creation) |
| incident_type | VARCHAR(50) | NOT NULL (values: accident, gas_leak) |
| severity | VARCHAR(50) | nullable (values: minor, moderate, severe) — set for accident type |
| severity_score | FLOAT | nullable (raw SVM confidence/score) |
| anomaly_score | FLOAT | nullable (GMM score, for gas_leak type) |
| latitude | FLOAT | NOT NULL |
| longitude | FLOAT | NOT NULL |
| status | VARCHAR(50) | NOT NULL, default 'open' (values: open, acknowledged, resolved, false_positive) |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |
| resolved_at | TIMESTAMPTZ | nullable |

Index: `(device_id, created_at)`, `(status)`

---

### 6. `alerts`
Notification dispatch log — mocked in Phase 1, real integration later.

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK, default gen_random_uuid() |
| incident_id | UUID | FK → incidents.id, NOT NULL |
| channel | VARCHAR(50) | NOT NULL (values: mock, email, sms — only 'mock' active in Phase 1) |
| recipient | VARCHAR(255) | nullable |
| payload | JSONB | NOT NULL (snapshot of what was "sent") |
| dispatched_at | TIMESTAMPTZ | NOT NULL, default now() |
| delivery_status | VARCHAR(50) | NOT NULL, default 'mocked' (values: mocked, sent, failed) |

### 7. `ambulances`
Emergency vehicle fleet registry and current location tracking (added Sprint 2).

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK, default gen_random_uuid() |
| ambulance_code | VARCHAR(100) | UNIQUE, NOT NULL (e.g. "AMB-001") |
| label | VARCHAR(255) | nullable (e.g. "Rapid Response Unit A") |
| current_latitude | FLOAT | nullable |
| current_longitude | FLOAT | nullable |
| status | VARCHAR(50) | NOT NULL, default 'available' (values: available, dispatched, en_route, at_scene, offline) |
| last_location_update | TIMESTAMPTZ | nullable |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |

Index: `(ambulance_code)` UNIQUE

---

### 8. `dispatches`
Human operator-triggered ambulance dispatch records (added Sprint 2).

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK, default gen_random_uuid() |
| incident_id | UUID | FK → incidents.id, NOT NULL |
| ambulance_id | UUID | FK → ambulances.id, NOT NULL |
| dispatched_by | UUID | FK → users.id, NOT NULL |
| status | VARCHAR(50) | NOT NULL, default 'dispatched' (values: dispatched, en_route, arrived, completed, cancelled) |
| dispatched_at | TIMESTAMPTZ | NOT NULL, default now() |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() |

### 9. `welfare_checks`
Automated victim check-in and response escalation records for severe accidents (added Sprint 3).

| Column | Type | Constraints |
|---|---|---|
| id | UUID | PK, default gen_random_uuid() |
| incident_id | UUID | FK → incidents.id, NOT NULL |
| device_id | UUID | FK → devices.id, NOT NULL |
| status | VARCHAR(50) | NOT NULL, default 'awaiting_response' (values: awaiting_response, responded_ok, responded_help, no_response_escalated) |
| initiated_at | TIMESTAMPTZ | NOT NULL, default now() |
| responded_at | TIMESTAMPTZ | nullable |
| response | VARCHAR(50) | nullable (values: ok, help) |
| escalated_at | TIMESTAMPTZ | nullable |

---

## Relationships
users (dashboard auth + dispatches.dispatched_by reference)

devices 1───* sensor_readings
devices 1───* incidents
devices 1───* welfare_checks
sensor_readings 1───1 incidents (an incident references the triggering reading)
hospitals 1───* incidents (nearest hospital optional relation)
incidents 1───* alerts
incidents 1───* dispatches
incidents 1───* welfare_checks
ambulances 1───* dispatches


## Migration Plan
- Alembic manages all schema changes from `backend/alembic/`.
- 0001_initial_schema: users -> devices -> sensor_readings -> incidents -> alerts.
- 0002_add_hospitals_table: creates `hospitals` table and adds `incidents.nearest_hospital_id` FK.
- 0003_add_ambulances_dispatches: creates `ambulances` and `dispatches` tables.
- 0004_add_welfare_checks: creates `welfare_checks` table.

## Notes
- UUID primary keys chosen over serial ints for future multi-device/distributed safety.
- `sensor_readings` is expected to be high-volume — indexed on `(device_id, recorded_at)` for dashboard time-series queries.
