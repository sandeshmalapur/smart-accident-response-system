# Smart Accident Response System — Complete Technical Explainer

This document serves as the canonical technical reference for the **Smart Accident Response System**. It is grounded directly in the actual source code as implemented on disk (`backend/`, `frontend/`, `ml/`, `simulator/`), explicitly highlighting design decisions, data flows, ML pipeline mechanics, database structures, and any historical discrepancies between earlier documentation (`docs/`) and the live codebase.

---

## 1. System Overview

The **Smart Accident Response System** is an end-to-end IoT and Edge-AI solution engineered to automatically detect vehicle collisions and hazardous gas leaks in real time, classify their severity using trained machine learning models, and instantly broadcast alerts to emergency operators via a live web dashboard. Telemetry payloads containing accelerometer motion, gyroscope rotation, MQ-2 gas concentrations, and GPS coordinates are published by vehicle devices (or software simulators) over MQTT to an Eclipse Mosquitto broker. A FastAPI backend subscribes to this telemetry, persists raw readings into a PostgreSQL database, executes dual machine learning models (a Support Vector Machine for collision severity classification and a Gaussian Mixture Model for gas anomaly detection), logs emergency incident and mock alert records, and broadcasts real-time state updates over WebSockets to a React/TypeScript dashboard for immediate triage and dispatch.

---

## 2. Full Architecture Diagram + Data Flow

### Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                            EDGE / PUBLISHER LAYER                                 |
|                                                                                   |
|   +------------------------------------+  +-----------------------------------+   |
|   | Python Sensor Simulator            |  | ESP32 Hardware Unit (Future Phase)|   |
|   | (simulator/sensor_simulator.py)    |  | (MPU6050 + MQ2 + GPS NEO-6M)      |   |
|   +-----------------+------------------+  +-----------------+-----------------+   |
+---------------------|---------------------------------------|---------------------+
                      | MQTT (safe/{device_code}/telemetry)   |
                      +-------------------+-------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                           BROKER & INGESTION LAYER                                |
|                                                                                   |
|                     +---------------------------------------+                     |
|                     | Eclipse Mosquitto MQTT Broker         |                     |
|                     | (Port 1883 / QoS 1)                   |                     |
|                     +-------------------+-------------------+                     |
|                                         |                                         |
|                                         v                                         |
|   FASTAPI BACKEND                       |                                         |
|   +-------------------------------------v-------------------------------------+   |
|   | MQTT Subscriber (app/mqtt/client.py)                                      |   |
|   |   1. JSON Deserialization & Pydantic Validation                           |   |
|   |   2. Device Code Resolution (app/services/device_service.py)               |   |
|   |   3. Persist Sensor Reading (app/services/reading_service.py)            |   |
|   |   4. Trigger ML Inference (app/ml/inference.py)                           |   |
|   +-----------------+-------------------+-------------------+-----------------+   |
+---------------------|-------------------|-------------------|---------------------+
                      |                   |                   |
                      v                   v                   v
+---------------------+-----+   +---------+---------+   +-----+---------------------+
| PERSISTENCE (PostgreSQL)  |   | MACHINE LEARNING  |   | WEBSOCKET BROADCAST       |
|                           |   | (app/ml/)         |   | (app/ws/manager.py)       |
|  - sensor_readings        |   |                   |   |                           |
|  - incidents              |   |  - SVM Severity   |   |  Pushes live JSON:        |
|  - alerts                 |   |  - GMM Anomaly    |   |   - { type: "reading" }   |
|  - devices                |   |                   |   |   - { type: "incident" }  |
|  - users                  |   |  Returns 0-2      |   |   - { type: "alert" }     |
|                           |   |  InferenceResults |   |                           |
+---------------------------+   +---------+---------+   +-----------+---------------+
                                          |                         |
                                          +------------+            |
                                                       |            |
                                                       v            v
+-----------------------------------------------------------------------------------+
|                             FRONTEND OPERATOR DASHBOARD                           |
|                                                                                   |
|   REACT / TYPESCRIPT DASHBOARD (frontend/src/)                                    |
|   +---------------------------------------------------------------------------+   |
|   | WS Client (useLiveFeed.ts)  <--- WS /api/v1/ws/live ----------------------+   |
|   |                                                                           |   |
|   | REST Client (api-client.ts) ---> REST /api/v1/ (Auth, Incidents, Devices) |   |
|   |                                                                           |   |
|   | Business Logic: annotateIncidentCoOccurrence() (lib/incident-utils.ts)   |   |
|   +---------------------------------------------------------------------------+   |
+-----------------------------------------------------------------------------------+
```

### Complete Request Trace

1. **Telemetry Publish**:
   The sensor simulator ([`simulator/sensor_simulator.py`](file:///d:/Desktop/major_project/smart-accident-response-system/simulator/sensor_simulator.py)) or an ESP32 microcontroller samples physical sensors every 200ms–1s and constructs a JSON payload containing `device_code`, `recorded_at`, `accel` `{x,y,z}`, `gyro` `{x,y,z}`, `gas_level`, and `gps` `{lat,lng}`. It publishes this payload to topic `safe/{device_code}/telemetry` over MQTT with Quality of Service 1 (QoS 1).

2. **MQTT Broker Processing**:
   The Eclipse Mosquitto broker accepts the TCP connection on port `1883` and delivers the message to all active subscribers registered on topic pattern `safe/+/telemetry`.

3. **Backend Subscriber Handling**:
   The Paho MQTT client in [`app/mqtt/client.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/mqtt/client.py) receives the message on paho's network thread. Its `_on_message` callback uses `asyncio.run_coroutine_threadsafe` to hop onto FastAPI's main asyncio event loop and executes `_handle_telemetry`:
   - **Schema Validation**: Validates the raw JSON dictionary against `MqttTelemetryPayload` ([`app/schemas/reading.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/schemas/reading.py)). Malformed non-JSON or invalid schema payloads are logged and dropped without crashing.
   - **Device Resolution**: Queries PostgreSQL for a matching `device_code` using `device_service.get_device_by_code`. If unknown, the message is dropped to prevent unauthorized injection.
   - **Persistence**: Writes a new row to `sensor_readings` via `reading_service.create_reading`.
   - **WebSocket Broadcast**: Immediately converts the saved `SensorReading` model into `SensorReadingOut` and invokes `manager.broadcast_reading()` to update live telemetry displays.
   - **Inference Handoff**: Extracts sensor values and passes them to `run_inference()`.

4. **ML Inference Pipeline**:
   Inside [`app/ml/inference.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/ml/inference.py), `run_inference()` calls the singleton `InferenceService` ([`app/ml/_inference_service.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/ml/_inference_service.py)):
   - **SVM Severity Classifier**: Computes features (`accel_magnitude`, `accel_axis_std`, `gyro_magnitude`, `jerk`) and runs `predict_severity()`. If the predicted class is `"moderate"` or `"severe"`, it creates an `InferenceResult` object with `incident_type="accident"`.
   - **GMM Anomaly Detector**: Computes features (`gas_level_norm`, `accel_magnitude`) and runs `predict_anomaly()`. If the log-likelihood score drops below `gmm_threshold`, it creates an `InferenceResult` object with `incident_type="gas_leak"`.
   - **Dual-Incident Design Return**: `run_inference()` returns a `list[InferenceResult]` containing **0, 1, or 2** items.

   > **Why `run_inference()` returns a list instead of a single result**:
   > In `DATABASE_SCHEMA.md`, `incidents.incident_type` is defined as a single string column (`"accident"` XOR `"gas_leak"`). A single severe crash reading can trip the SVM model (high acceleration impact) AND the GMM anomaly model simultaneously (since GMM is a joint model evaluating acceleration along with gas). To represent both findings without altering the single-enum database schema, `run_inference()` returns two separate `InferenceResult` objects. The MQTT subscriber iterates through the returned list and creates **two distinct incident rows** in PostgreSQL that share the same `sensor_reading_id`.

5. **Incident Persistence**:
   For each item in `results`, `client.py` calls `incident_service.create_incident_from_inference()` ([`app/services/incident_service.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/services/incident_service.py)), writing an `Incident` row into PostgreSQL.

6. **Alert Dispatch**:
   `client.py` calls `alert_service.dispatch_mock_alert()` ([`app/services/alert_service.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/services/alert_service.py)), which creates an `Alert` database record with `channel="mock"` and `delivery_status="mocked"`.

7. **WebSocket Broadcast**:
   `client.py` serializes the created `Incident` and `Alert` records into Pydantic models (`IncidentOut` and `AlertOut`) and broadcasts them to all connected clients via `manager.broadcast_incident()` and `manager.broadcast_alert()` ([`app/ws/manager.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/ws/manager.py)).

8. **Frontend WebSocket Client**:
   The custom hook [`useLiveFeed.ts`](file:///d:/Desktop/major_project/smart-accident-response-system/frontend/src/hooks/useLiveFeed.ts) maintains a persistent WebSocket connection to `/api/v1/ws/live?token=...`. When a message arrives, it updates local state (`latestReadings`, `recentReadings`, `liveIncidents`, `liveAlerts`), triggering instant React UI re-renders.

9. **Frontend REST Queries**:
   - [`useAuth.ts`](file:///d:/Desktop/major_project/smart-accident-response-system/frontend/src/hooks/useAuth.ts): Calls `POST /api/v1/auth/login` to authenticate and `GET /api/v1/auth/me` to verify user session.
   - [`useDevices.ts`](file:///d:/Desktop/major_project/smart-accident-response-system/frontend/src/hooks/useDevices.ts): Calls `GET /api/v1/devices` to fetch registered devices.
   - [`useIncidents.ts`](file:///d:/Desktop/major_project/smart-accident-response-system/frontend/src/hooks/useIncidents.ts): Calls `GET /api/v1/incidents` to load historical incident logs or lookup sibling incidents, and uses `PATCH /api/v1/incidents/{id}` to update triage status (`open`, `acknowledged`, `resolved`, `false_positive`).

---

## 3. Database Schema (as actually implemented)

The database schema is implemented in [`backend/app/db/models.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/db/models.py) using SQLAlchemy 2.0 mapped columns, targeting PostgreSQL.

```
       +-------------------+
       |       users       |
       +-------------------+
       | id (PK)           |
       | email (UNIQUE)    |
       | hashed_password   |
       | full_name         |
       | role              |
       | is_active         |
       | created_at        |
       +-------------------+

       +-------------------+            +---------------------------------+
       |      devices      |            |         sensor_readings         |
       +-------------------+            +---------------------------------+
       | id (PK)           | 1        * | id (PK)                         |
       | device_code (UNIQ)|------------| device_id (FK -> devices.id)    |
       | device_type       |            | accel_x, accel_y, accel_z       |
       | label             |            | gyro_x, gyro_y, gyro_z (null)   |
       | is_active         |            | gas_level                       |
       | created_at        |            | latitude, longitude             |
       +---------+---------+            | recorded_at, received_at        |
                 |                      +----------------+----------------+
                 | 1                                     | 1
                 |                                       |
                 | *                                     | * (Non-Unique FK)
       +---------v---------+                             |
       |     incidents     |<----------------------------+
       +-------------------+
       | id (PK)           |
       | device_id (FK)    |
       | sensor_reading_id | (FK -> sensor_readings.id)
       | incident_type     | ('accident' | 'gas_leak')
       | severity          | ('minor' | 'moderate' | 'severe')
       | severity_score    | (Float, nullable)
       | anomaly_score     | (Float, nullable)
       | latitude, long... |
       | status            | ('open' | 'acknowledged' | 'resolved' | 'false_positive')
       | created_at        |
       | resolved_at       |
       +---------+---------+
                 | 1
                 |
                 | *
       +---------v---------+
       |      alerts       |
       +-------------------+
       | id (PK)           |
       | incident_id (FK)  | (FK -> incidents.id)
       | channel           | ('mock' | 'email' | 'sms')
       | recipient         |
       | payload (JSONB)   |
       | dispatched_at     |
       | delivery_status   | ('mocked' | 'sent' | 'failed')
       +-------------------+
```

### Table Definitions & Columns

1. **`users`**: Dashboard operator accounts.
   - `id`: `UUID`, Primary Key (`uuid4`)
   - `email`: `String(255)`, `UNIQUE`, `NOT NULL`
   - `hashed_password`: `String(255)`, `NOT NULL`
   - `full_name`: `String(255)`, `NOT NULL`
   - `role`: `String(50)`, `NOT NULL`, default `"operator"`
   - `is_active`: `Boolean`, `NOT NULL`, default `True`
   - `created_at`: `DateTime(timezone=True)`, `NOT NULL`, default `func.now()`

2. **`devices`**: Registered physical or simulated devices.
   - `id`: `UUID`, Primary Key (`uuid4`)
   - `device_code`: `String(100)`, `UNIQUE`, `NOT NULL` (e.g., `"SIM-001"`)
   - `device_type`: `String(50)`, `NOT NULL` (`"simulator"` or `"esp32"`)
   - `label`: `String(255)`, Nullable
   - `is_active`: `Boolean`, `NOT NULL`, default `True`
   - `created_at`: `DateTime(timezone=True)`, `NOT NULL`, default `func.now()`

3. **`sensor_readings`**: Ingested time-series telemetry.
   - `id`: `UUID`, Primary Key (`uuid4`)
   - `device_id`: `UUID`, Foreign Key → `devices.id`, `NOT NULL`
   - `accel_x`, `accel_y`, `accel_z`: `Float`, `NOT NULL` (m/s²)
   - `gyro_x`, `gyro_y`, `gyro_z`: `Float`, Nullable (deg/s)
   - `gas_level`: `Float`, `NOT NULL` (MQ-2 analog range 0–1023)
   - `latitude`, `longitude`: `Float`, `NOT NULL`
   - `recorded_at`: `DateTime(timezone=True)`, `NOT NULL` (device timestamp)
   - `received_at`: `DateTime(timezone=True)`, `NOT NULL`, default `func.now()`
   - *Index*: `ix_sensor_readings_device_id_recorded_at` on `(device_id, recorded_at)`

4. **`incidents`**: Machine learning flagged events.
   - `id`: `UUID`, Primary Key (`uuid4`)
   - `device_id`: `UUID`, Foreign Key → `devices.id`, `NOT NULL`
   - `sensor_reading_id`: `UUID`, Foreign Key → `sensor_readings.id`, `NOT NULL` (**Non-unique FK**)
   - `incident_type`: `String(50)`, `NOT NULL` (`"accident"` or `"gas_leak"`)
   - `severity`: `String(50)`, Nullable (`"minor"`, `"moderate"`, `"severe"`)
   - `severity_score`: `Float`, Nullable (SVM probability)
   - `anomaly_score`: `Float`, Nullable (GMM log-likelihood)
   - `latitude`, `longitude`: `Float`, `NOT NULL`
   - `status`: `String(50)`, `NOT NULL`, default `"open"` (`"open"`, `"acknowledged"`, `"resolved"`, `"false_positive"`)
   - `created_at`: `DateTime(timezone=True)`, `NOT NULL`, default `func.now()`
   - `resolved_at`: `DateTime(timezone=True)`, Nullable
   - *Indexes*: `ix_incidents_device_id_created_at` on `(device_id, created_at)`, `ix_incidents_status` on `(status)`

5. **`alerts`**: Emergency dispatch log.
   - `id`: `UUID`, Primary Key (`uuid4`)
   - `incident_id`: `UUID`, Foreign Key → `incidents.id`, `NOT NULL`
   - `channel`: `String(50)`, `NOT NULL` (`"mock"`, `"email"`, `"sms"`)
   - `recipient`: `String(255)`, Nullable
   - `payload`: `JSONB`, `NOT NULL`
   - `dispatched_at`: `DateTime(timezone=True)`, `NOT NULL`, default `func.now()`
   - `delivery_status`: `String(50)`, `NOT NULL`, default `"mocked"` (`"mocked"`, `"sent"`, `"failed"`)

### The Non-Unique `sensor_reading_id` Foreign Key

In traditional relational modeling, linking an incident to its triggering sensor reading might use a `UNIQUE` constraint on `sensor_reading_id` to enforce a 1-to-1 relationship. However, in this system, **`incidents.sensor_reading_id` is deliberately non-unique**.

When a severe vehicle crash occurs, the telemetry payload contains extreme acceleration spikes. When passed through `run_inference()`, this single reading simultaneously triggers:
1. The **SVM severity model** (identifying a `"severe"` vehicle collision).
2. The **GMM anomaly model** (because extreme acceleration shifts the sample into a low-probability region of the joint `[gas_level_norm, accel_magnitude]` space).

Because `incidents.incident_type` is a single enum value (`"accident"` XOR `"gas_leak"`), the backend generates **two distinct rows in `incidents`** for that single reading—one row for the accident and one row for the gas anomaly. Both rows reference the identical `sensor_reading_id`.

---

## 4. The ML Pipeline in Detail

### Synthetic Data Generation ([`ml/training/generate_synthetic_data.py`](file:///d:/Desktop/major_project/smart-accident-response-system/ml/training/generate_synthetic_data.py))

Because real-world telemetry during severe vehicular collisions is unavailable, synthetic data is generated to train the models:
- **Rows**: 6,000 total rows (2,000 for each severity class: `minor`, `moderate`, `severe`).
- **Data Shape**: Column names match `sensor_readings` exactly (`accel_x/y/z`, `gyro_x/y/z`, `gas_level`, `latitude`, `longitude`).
- **Gas Anomaly Injection**: Independently overlays anomalous gas readings on 8% of all rows (`GAS_ANOMALY_RATE = 0.08`), drawing `gas_level` from a Gaussian distribution $N(750, 130)$ clipped to $[400, 1023]$. This ensures gas anomalies occur across both normal driving and impact events.

### Feature Breakdown ([`ml/training/features.py`](file:///d:/Desktop/major_project/smart-accident-response-system/ml/training/features.py))

| Model | Feature Name | Computation Formula / Source | Rationale |
|---|---|---|---|
| **SVM** | `accel_magnitude` | $\sqrt{a_x^2 + a_y^2 + a_z^2}$ | Overall G-force acceleration magnitude. |
| **SVM** | `accel_axis_std` | $\text{std}([a_x, a_y, a_z])$ | Multi-axis dispersion (distinguishes linear braking from multi-axis rollover). |
| **SVM** | `gyro_magnitude` | $\sqrt{g_x^2 + g_y^2 + g_z^2}$ | Rotational velocity (detects vehicle spin/flip). |
| **SVM** | `jerk` | $\frac{\text{accel\_mag} - \text{prev\_accel\_mag}}{\Delta t}$ | Acceleration rate of change between consecutive readings. |
| **GMM** | `gas_level_norm` | $\text{clip}\left(\frac{\text{gas\_level}}{1023.0}, 0.0, 1.0\right)$ | Scaled MQ-2 analog reading. |
| **GMM** | `accel_magnitude` | $\sqrt{a_x^2 + a_y^2 + a_z^2}$ | Included to model the joint distribution of gas level and motion dynamics. |

### Diagnostic History: The Gravity Omission Bug

During early development, an isolation test revealed that normal simulated driving triggered false-positive accident classifications across all samples. 

- **Diagnosis**: Analysis of `generate_synthetic_data.py` showed that `_gen_minor()` was generating Z-axis acceleration centered around $0.0\text{ m/s}^2$ rather than Earth gravity ($g \approx 9.81\text{ m/s}^2$). When real driving telemetry was evaluated by the trained model, the presence of standard gravitational acceleration caused `accel_magnitude` to equal $\sim 9.81\text{ m/s}^2$, which fell directly into the model's trained range for moderate impacts.
- **Fix**: The synthetic generator was updated to center Z-axis acceleration around Earth's gravity for minor driving:
  ```python
  az = float(rng.normal(GRAVITY_Z, 0.3))  # GRAVITY_Z = 9.81 m/s^2
  ```

### GMM Co-Occurrence Behavior & Frontend Disambiguation

Because the GMM anomaly detector is trained on the joint distribution `[gas_level_norm, accel_magnitude]`, a severe crash reading with extreme G-force (e.g., $a_{\text{mag}} = 45\text{ m/s}^2$) drops the log-likelihood score calculated by `gmm.score_samples()` below the detection threshold (`threshold_percentile = 2.0`). As a result, the GMM flags a `gas_leak` anomaly even when the MQ-2 sensor reports normal ambient gas levels ($\sim 200\text{ ppm}$).

To prevent false gas leak alarms from confusing emergency dispatchers, the frontend implements the `annotateIncidentCoOccurrence()` transformation ([`frontend/src/lib/incident-utils.ts`](file:///d:/Desktop/major_project/smart-accident-response-system/frontend/src/lib/incident-utils.ts)):

```typescript
export function annotateIncidentCoOccurrence(incidents: Incident[]): AnnotatedIncident[] {
  const accidentReadingIds = new Set<string>();
  for (const inc of incidents) {
    if (inc.incident_type === 'accident' && inc.sensor_reading_id) {
      accidentReadingIds.add(inc.sensor_reading_id);
    }
  }

  return incidents.map((inc) => {
    if (inc.incident_type === 'gas_leak') {
      const hasSiblingAccident = Boolean(inc.sensor_reading_id && accidentReadingIds.has(inc.sensor_reading_id));
      if (hasSiblingAccident) {
        return {
          ...inc,
          isCoOccurringGasLeak: true,
          displayTitle: 'Gas anomaly detected during accident',
          badgeVariant: 'gas-secondary',
        };
      }
      return {
        ...inc,
        isCoOccurringGasLeak: false,
        displayTitle: 'Gas Leak Anomaly Detected',
        badgeVariant: 'gas-critical',
      };
    }
    // ... formatting for accident type
  });
}
```

---

## 5. Every API Endpoint

Defined across routers in [`backend/app/api/`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/api/). Base URL prefix: `/api/v1`.

| Route | Method | Auth Required | Router File | Description & Query Parameters |
|---|---|---|---|---|
| `/health` | `GET` | None | [`main.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/main.py#L48) | System health check endpoint. Returns `{"status": "ok"}`. |
| `/api/v1/auth/login` | `POST` | None | [`auth.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/api/auth.py#L14) | Authenticates email/password. Returns JWT access token and user object. |
| `/api/v1/auth/me` | `GET` | Bearer Token | [`auth.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/api/auth.py#L23) | Returns currently authenticated user details. |
| `/api/v1/devices` | `GET` | Bearer Token | [`devices.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/api/devices.py#L14) | Lists registered devices. Optional query param: `is_active` (bool). |
| `/api/v1/devices` | `POST` | Admin Token | [`devices.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/api/devices.py#L20) | Registers a new device (`device_code`, `device_type`, `label`). |
| `/api/v1/devices/{device_id}` | `GET` | Bearer Token | [`devices.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/api/devices.py#L29) | Retrieves a single device record by UUID. |
| `/api/v1/readings` | `GET` | Bearer Token | [`readings.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/api/readings.py#L15) | Lists historical sensor readings. Query params: `device_id`, `from`, `to`, `limit` (default 100, max 1000). |
| `/api/v1/readings/latest` | `GET` | Bearer Token | [`readings.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/api/readings.py#L27) | Returns the most recent reading per device. Query param: `device_id`. |
| `/api/v1/incidents` | `GET` | Bearer Token | [`incidents.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/api/incidents.py#L16) | Lists historical incidents. Query params: `status`, `incident_type`, `device_id`, **`sensor_reading_id`**, `from`, `to`, `limit` (default 50). |
| `/api/v1/incidents/{incident_id}` | `GET` | Bearer Token | [`incidents.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/api/incidents.py#L40) | Retrieves single incident detail, eagerly loading nested `sensor_reading` and `alerts`. |
| `/api/v1/incidents/{incident_id}` | `PATCH` | Bearer Token | [`incidents.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/api/incidents.py#L48) | Updates incident triage status (`open`, `acknowledged`, `resolved`, `false_positive`). Broadcasts update over WS. |
| `/api/v1/alerts` | `GET` | Bearer Token | [`alerts.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/api/alerts.py#L14) | Lists emergency alert logs. Query params: `incident_id`, `limit` (default 50). |
| `/api/v1/ws/live` | `WS` | Query Token | [`ws.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/api/ws.py#L13) | Broadcast-only WebSocket stream (`?token=...`). Pushes `reading`, `incident`, and `alert` JSON envelopes. |

> **Note on `GET /api/v1/incidents?sensor_reading_id=...`**:
> The `sensor_reading_id` filter parameter was specifically added to allow the frontend (`IncidentDetailPage.tsx`) to query for all sibling incidents sharing the same triggering sensor reading. This is required for client-side co-occurrence disambiguation.

---

## 6. Frontend Structure

Built with React 18, TypeScript, Vite, Tailwind CSS, and Lucide React icons.

```
frontend/src/
├── App.tsx                    # Router setup & query client provider
├── components/
│   ├── IncidentCard.tsx       # Live feed incident cards
│   ├── MapView.tsx            # Leaflet radar map component
│   ├── Navbar.tsx             # Top navigation & WS status indicator
│   ├── ProtectedRoute.tsx     # JWT auth guard wrapper
│   ├── Sidebar.tsx            # Navigation sidebar
│   └── StatusBadge.tsx        # Dynamic severity & status badges
├── hooks/
│   ├── useAuth.ts             # Auth context & JWT token management
│   ├── useDevices.ts          # TanStack Query hook for devices API
│   ├── useIncidents.ts        # TanStack Query hook for incidents API
│   └── useLiveFeed.ts         # WebSocket client & real-time feed state
├── lib/
│   ├── api-client.ts          # Axios REST client with JWT interceptor
│   ├── incident-utils.ts      # annotateIncidentCoOccurrence utility
│   └── types.ts               # Shared TypeScript interfaces
└── pages/
    ├── DashboardPage.tsx      # Main operational dashboard
    ├── DevicesPage.tsx        # Device inventory & registration page
    ├── IncidentDetailPage.tsx # Incident dossier & triage view
    ├── IncidentsPage.tsx      # Historical incident audit table
    └── LoginPage.tsx          # Operator login view
```

### Page Breakdown & Business Rules

1. **`LoginPage.tsx`**:
   Renders operator login form. Sends `POST /api/v1/auth/login`, stores JWT token in `localStorage`, and redirects to `/dashboard`.

2. **`DashboardPage.tsx`**:
   The primary command center. Combines historical REST incidents (`useIncidents`) with incoming WebSocket incidents (`useLiveFeed`).
   - Runs `annotateIncidentCoOccurrence()` on the combined incident set.
   - Computes live KPI cards: Active Devices, Severe Accidents, Standalone Gas Leaks, and Co-occurring Gas Anomalies.
   - Renders interactive Leaflet map (`MapView`) showing vehicle positions and active incident hotspots.
   - Displays live sensor telemetry per device (accelerometer vector magnitude, MQ-2 gas levels, GPS).

3. **`IncidentsPage.tsx`**:
   Audit table for historical triage. Applies `annotateIncidentCoOccurrence()` to raw incidents before applying status/type UI filters. Shows badge variants, device codes, truncated reading IDs, GPS coordinates, and navigation links.

4. **`IncidentDetailPage.tsx`**:
   Detailed incident dossier.
   - Fetches the primary incident via `useIncident(id)`.
   - Fetches sibling incidents sharing `sensor_reading_id` via `useIncidents({ sensor_reading_id })`.
   - Passes `[incident, ...siblings]` through `annotateIncidentCoOccurrence()`. If flagged as a co-occurring anomaly, displays an alert banner explaining that the GMM anomaly was induced by acceleration G-force spikes.
   - Renders triggering sensor reading snapshot and notification dispatch log.
   - Provides status triage dropdown allowing operators to issue `PATCH /api/v1/incidents/{id}`.

5. **`DevicesPage.tsx`**:
   Device management inventory. Displays active/inactive state and device codes, and allows admins to register new simulator/ESP32 devices via `POST /api/v1/devices`.

---

## 7. The Simulator

Located in `simulator/` ([`sensor_simulator.py`](file:///d:/Desktop/major_project/smart-accident-response-system/simulator/sensor_simulator.py) and [`scenarios.py`](file:///d:/Desktop/major_project/smart-accident-response-system/simulator/scenarios.py)).

### Scenarios

| Scenario Name | Class | Accel Dynamics (m/s²) | Gyro Dynamics (deg/s) | Gas Level (0–1023) | Description |
|---|---|---|---|---|---|
| `normal` | `NormalScenario` | $a_x, a_y \sim N(0, 0.08)$<br>$a_z \sim N(9.81, 0.05)$ | $g_x, g_y, g_z \sim N(0, 0.5)$ | Noise around baseline ($\sim 80-130$) | Baseline driving with slight GPS drift. |
| `moderate_impact` | `ModerateImpactScenario` | Ticks 10–12: Spike magnitude $\pm 18.0$ m/s² | Ticks 10–12: Spike magnitude $\pm 120.0$ deg/s | Baseline ($\sim 80-130$) | Moderate collision spike, followed by stopped vehicle motion. |
| `severe_crash` | `SevereCrashScenario` | Ticks 10–14: Spike magnitude $\pm 45.0$ m/s² | Ticks 10–14: Spike magnitude $\pm 350.0$ deg/s | Baseline ($\sim 80-130$) | Severe collision spike + vehicle spin/flip, followed by stopped state. |
| `gas_leak` | `GasLeakScenario` | Normal driving motion | Normal driving rotation | Ticks 8–18: Ramps steadily up to $\sim 700.0$ | Sustained gas leak elevation over time. |

### Running the Simulator

```bash
# Basic run with default 'normal' scenario (Ctrl+C to stop)
python simulator/sensor_simulator.py --device-code SIM-001

# Run a severe crash scenario for 30 seconds
python simulator/sensor_simulator.py --device-code SIM-001 --scenario severe_crash --duration 30

# Run a gas leak scenario against a custom MQTT broker
python simulator/sensor_simulator.py --device-code SIM-001 --scenario gas_leak --broker-host 127.0.0.1 --broker-port 1883
```

---

## 8. How Everything Connects — Full Local Run Sequence

To start the complete stack locally from scratch:

### 1. Launch Docker Infrastructure
Starts PostgreSQL 16 and Mosquitto MQTT broker containers in the background:
```bash
docker compose up -d postgres mosquitto
```

### 2. Synchronize ML Artifacts
Copies trained model files (`svm_severity.joblib`, `gmm_anomaly.joblib`, `model_metadata.json`) and feature modules from root `ml/` into `backend/app/ml/`:
```bash
cd backend
python -m app.ml.sync_models
```

### 3. Seed Database
Applies initial schema migrations (via Alembic) and creates default test entities (`admin@example.com` / `changeme123` and device `SIM-001`):
```bash
# Ensure virtual environment is active
venv\Scripts\activate
python -m scripts.seed
```

### 4. Start FastAPI Backend
Launches the FastAPI server with live reloading enabled:
```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Start React Frontend
In a separate terminal, launch the Vite development server:
```bash
cd frontend
npm run dev
```

### 6. Run Sensor Simulator
In a separate terminal, publish simulated sensor data to trigger detection pipeline:
```bash
python simulator/sensor_simulator.py --device-code SIM-001 --scenario severe_crash --duration 30
```

---

## 9. Known Limitations & Honest Caveats

1. **Synthetic Training Data**:
   The SVM and GMM models were trained exclusively on synthetic distributions generated by `generate_synthetic_data.py`. No physical collision or real MQ-2 hardware sensor datasets have been collected or incorporated yet.

2. **Mocked Emergency Alerts**:
   The alert dispatch module (`alert_service.py`) generates database records with `channel="mock"` and `delivery_status="mocked"`. External SMS (Twilio) or email dispatch integrations are stubs planned for future development phases.

3. **Docker Postgres Credential Requirement**:
   Local execution depends on Docker Postgres because default database credentials (`safe_user` / `safe_password` / `safe_accident_db`) are hardcoded across `docker-compose.yml` and `.env.example`.

4. **In-Memory Device Status**:
   Device online/offline heartbeat statuses received on `safe/{device_code}/status` are stored in an in-memory dictionary (`_device_status`) inside `MqttSubscriber` ([`client.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/mqtt/client.py#L47)) rather than being written to a database table.

5. **Broadcast-Only WebSocket Channel**:
   The `/api/v1/ws/live` endpoint is broadcast-only. Any incoming text messages sent from clients to the server are drained and ignored.

---

## 10. Glossary

- **Co-occurrence**: The condition where a single sensor reading triggers both an SVM collision severity alert and a GMM anomaly detection alert due to multi-variate feature overlap.
- **Dual-Incident Design**: The architecture pattern where `run_inference()` returns `list[InferenceResult]` (0–2 items) and the backend creates two distinct database rows sharing a single `sensor_reading_id`.
- **Telemetry**: Real-time sensor payloads transmitted over MQTT containing accelerometer, gyroscope, gas level, and GPS coordinates.
- **GMM (Gaussian Mixture Model)**: Unsupervised probabilistic model used to detect anomalous gas levels and abnormal sensor readings.
- **SVM (Support Vector Machine)**: Supervised classifier used to evaluate collision severity (`minor`, `moderate`, `severe`).
- **`sensor_reading_id` Sibling Lookup**: Querying the `incidents` table for other incident records sharing the same `sensor_reading_id` to determine co-occurrence.
- **MQ-2**: Analog gas sensor simulated in the range 0–1023.
- **MPU-6050**: 6-axis motion tracking sensor (3-axis accelerometer + 3-axis gyroscope).
- **QoS 1**: Quality of Service Level 1 in MQTT (guarantees at-least-once message delivery).
- **LWT (Last Will and Testament)**: MQTT feature where the broker automatically publishes a disconnection message when a client ungracefully drops connection.

---

## 11. Documented Code vs. Docs Discrepancies

| Topic / Feature | Description in `docs/` | Actual Implementation in Code | Ground Truth Resolution |
|---|---|---|---|
| **WebSocket Path** | Historical documentation referred to WebSocket mounting at `/ws/live`. | `backend/app/main.py` mounts `ws.router` under `API_PREFIX = "/api/v1"`, establishing the path at `/api/v1/ws/live`. | **Code is correct**: Frontend connects to `/api/v1/ws/live`. |
| **`sensor_readings` ↔ `incidents` Relationship** | `DATABASE_SCHEMA.md` initially depicted a strict 1-to-1 relationship between `sensor_readings` and `incidents`. | `incidents.sensor_reading_id` is a non-unique FK column in [`models.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/db/models.py#L86). Multiple incident rows can share a single reading ID. | **Code is correct**: Non-unique FK is required for the Dual-Incident design. |
| **Device Status Persistence** | `MQTT_SPEC.md` mentioned persisting device online/offline status in a database table. | Statuses received on `safe/{device_code}/status` are stored in an in-memory dictionary `_device_status` within [`client.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/mqtt/client.py#L47). | **Code is correct**: Kept in-memory to preserve the frozen 5-table schema. |
| **GET /incidents Parameters** | `API_SPEC.md` initially omitted `sensor_reading_id` from list query parameters. | `list_incidents()` in [`incidents.py`](file:///d:/Desktop/major_project/smart-accident-response-system/backend/app/api/incidents.py#L21) explicitly accepts `sensor_reading_id: uuid.UUID | None = None`. | **Code is correct**: Required by the frontend to fetch sibling incidents. |
