# Smart Accident Response System — Setup & Execution Guide

Complete end-to-end guide to set up, initialize, and run all components of the Smart Accident Response System on Windows without errors.

---

## 📑 Table of Contents
1. [System Architecture & Startup Order](#1-system-architecture--startup-order)
2. [Prerequisites](#2-prerequisites)
3. [Step 1: Start Infrastructure (Docker)](#3-step-1-start-infrastructure-docker)
4. [Step 2: Start Backend (FastAPI)](#4-step-2-start-backend-fastapi)
5. [Step 3: Start Frontend (React + Vite)](#5-step-3-start-frontend-react--vite)
6. [Step 4: Access Dashboard & Login](#6-step-4-access-dashboard--login)
7. [Step 5: Run Sensor & Accident Simulator](#7-step-5-run-sensor--accident-simulator)
8. [Service Endpoints & Credentials](#8-service-endpoints--credentials)
9. [Windows Troubleshooting & Fixes](#9-windows-troubleshooting--fixes)

---

## 1. System Architecture & Startup Order

To prevent connection failures, always launch components in the following sequence:

```
┌───────────────────────────────────────────────┐
│ 1. Docker Containers (PostgreSQL & Mosquitto) │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│ 2. FastAPI Backend (Migrations + Seed + API)  │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│ 3. React Frontend (Command Center Dashboard)  │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│ 4. Simulator (Feeds simulated crashes/leaks)  │
└───────────────────────────────────────────────┘
```

---

## 2. Prerequisites

Ensure the following tools are installed:
- **Docker Desktop** (running with Linux containers enabled)
- **Python 3.10 or 3.11** (with `pip`)
- **Node.js 18+ or 20+** (with `npm`)

---

## 3. Step 1: Start Infrastructure (Docker)

Open **Terminal 1** (PowerShell or Command Prompt) at the repository root:

```powershell
cd d:\Desktop\major_project\smart-accident-response-system
docker compose up -d
```

### Verify Running Containers:
```powershell
docker ps
```
You should see:
- `safe-postgres` listening on port `5433:5432`
- `safe-mosquitto` listening on ports `1883` and `9001`

*(Note: Postgres is mapped to host port `5433` to prevent conflicts with any locally installed PostgreSQL running on port 5432).*

---

## 4. Step 2: Start Backend (FastAPI)

Open **Terminal 2** for the Python backend:

```powershell
cd d:\Desktop\major_project\smart-accident-response-system\backend
```

### 1. Enable Script Execution in PowerShell
If PowerShell blocks virtual environment scripts, run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 2. Activate Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
```
*(If using standard Command Prompt CMD, use `.\venv\Scripts\activate.bat`)*

### 3. Verify / Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Apply Database Migrations
Applies Alembic schema migrations (users, devices, readings, incidents, hospitals, ambulances, dispatches):
```powershell
alembic upgrade head
```

### 5. Seed Test Data (Idempotent)
Populates default admin user, test vehicle device (`SIM-001`), sample hospitals, active ambulances (`AMB-001`, `AMB-002`, `AMB-003`), and police/fire units:
```powershell
python -m scripts.seed
```

### 6. Run the FastAPI Server
> **IMPORTANT (Windows):** Always pass `--host 127.0.0.1` so Uvicorn binds explicitly to IPv4.

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Verify Backend:
- Terminal logs should confirm:
  - `MQTT subscriber started`
  - `MQTT connected to localhost:1883`
  - `Application startup complete.`
- Test in browser:
  - Health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) → returns `{"status":"ok"}`
  - Interactive API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

> **Keep Terminal 2 running in the background.**

---

## 5. Step 3: Start Frontend (React + Vite)

Open **Terminal 3** for the frontend:

```powershell
cd d:\Desktop\major_project\smart-accident-response-system\frontend
```

### 1. Install Node Dependencies
```powershell
npm install
```

### 2. Start Vite Dev Server
```powershell
npm run dev
```

The frontend will start at:
👉 **[http://localhost:5173](http://localhost:5173)**

> **Keep Terminal 3 running in the background.**

---

## 6. Step 4: Access Dashboard & Login

1. Open your browser and navigate to **[http://localhost:5173](http://localhost:5173)**.
2. Sign in with the seeded operator credentials:
   - **Operator Email:** `admin@example.com`
   - **Password:** `changeme123`
3. Click **Sign In to Dashboard**.
4. You can navigate between:
   - **Command Center Dashboard** (`/dashboard`): Real-time KPI summaries, telemetry charts, and live incident stream.
   - **Dedicated GIS Radar Map** (`/map`): Full-screen operations map with layer toggles (Ambulances, Hospitals, Police/Fire, Incidents) and a live fleet inspector panel with smooth camera fly-to focusing.
   - **Incident Records** (`/incidents`): Complete emergency log and dispatch management.
   - **Ambulance Fleet** (`/ambulances`): Active unit status and driver telemetry cockpits.

---

## 7. Step 5: Run Sensor & Accident Simulator

To test the system with live sensor data and automatic incident triggering, open **Terminal 4**:

```powershell
cd d:\Desktop\major_project\smart-accident-response-system\simulator
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run any of the following scenarios:

### Scenario A: Severe Crash (Triggers Real Accident Incident)
Spikes accelerometer and gyroscope readings to simulate a high-impact crash:
```powershell
python sensor_simulator.py --device-code SIM-001 --scenario severe_crash --duration 30
```
- The backend's real SVM model (`svm_severity.joblib`) detects a **severe accident**.
- An incident row and alert are generated and broadcast via WebSockets live to the frontend map.

### Scenario B: Gas Leak Detection
Gradually ramps up gas sensor levels:
```powershell
python sensor_simulator.py --device-code SIM-001 --scenario gas_leak --duration 30
```
- The backend's GMM model (`gmm_anomaly.joblib`) flags an anomaly and creates a gas leak incident.

### Scenario C: Normal Vehicle Driving
Simulates normal vehicle driving telemetry without triggering incidents:
```powershell
python sensor_simulator.py --device-code SIM-001 --scenario normal --duration 30
```

### Scenario D: Ambulance Location Tracking
Simulates real-time ambulance movement toward a dispatched incident:
```powershell
python ambulance_simulator.py --ambulance-code AMB-001 --duration 60
```

---

## 8. Service Endpoints & Credentials

| Service | Address / URL | Credentials / Details |
| :--- | :--- | :--- |
| **Frontend Web App** | [http://localhost:5173](http://localhost:5173) | Operator UI |
| **Backend API Docs (Swagger)** | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | Interactive testing |
| **Backend Health Check** | [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) | Returns `{"status":"ok"}` |
| **Admin Login** | On Frontend or `/api/v1/auth/login` | `admin@example.com` / `changeme123` |
| **Pre-seeded Device** | Device Code | `SIM-001` |
| **PostgreSQL Database** | `127.0.0.1:5433` | User: `safe_user`, Pass: `safe_password`, DB: `safe_accident_db` |
| **Mosquitto MQTT Broker** | `127.0.0.1:1883` | Anonymous auth allowed |

---

## 9. Windows Troubleshooting & Fixes

### 1. `404 (Not Found)` on `/api/v1/auth/login`
- **Cause:** On Windows, Node.js (v18+) resolves `localhost` to IPv6 `::1`, while Uvicorn defaults to IPv4 `127.0.0.1`.
- **Fix:**
  1. Make sure `vite.config.ts` uses `target: 'http://127.0.0.1:8000'`.
  2. Start Uvicorn with `--host 127.0.0.1`:
     ```powershell
     uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
     ```

### 2. PowerShell: `File ... cannot be loaded because running scripts is disabled`
- **Cause:** PowerShell script execution policy restriction.
- **Fix:** Run this command in the terminal session:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```

### 3. Database Connection Error (`connection refused on 127.0.0.1:5433`)
- **Cause:** Docker Desktop is stopped or the container isn't running.
- **Fix:** Start Docker Desktop and run:
  ```powershell
  docker compose up -d
  ```

### 4. `ModuleNotFoundError: No module named 'scripts'`
- **Cause:** Running seeding command from the wrong folder.
- **Fix:** Always ensure you are inside the `backend/` directory:
  ```powershell
  cd backend
  python -m scripts.seed
  ```
