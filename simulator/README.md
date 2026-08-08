# Sensor Simulator

Standalone script that publishes fake sensor telemetry to MQTT, mimicking
a real ESP32 device, matching `MQTT_SPEC.md` exactly. Used to exercise the
already-working backend (Sprint S2) and ML pipeline (Sprint S3) end-to-end
without real hardware.

## Setup

```bash
cd simulator
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Before running: seed a test device

The backend **drops telemetry for any `device_code` it doesn't recognize**
(this is correct, intentional behavior — see `MQTT_SPEC.md`). A device
must exist in the `devices` table first.

If you already ran the backend's seed script (`python -m scripts.seed`
from `backend/`), device `SIM-001` already exists and you can skip ahead.

Otherwise, create one via the API (needs an admin JWT — see
`backend/README.md` for how to log in and get a token):

```bash
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"device_code": "SIM-001", "device_type": "simulator", "label": "Simulator Test Vehicle"}'
```

## Make sure the broker is running

```bash
# from repo root
docker compose up -d postgres mosquitto
```

## Running

Normal driving, runs until you press Ctrl+C:

```bash
python sensor_simulator.py --device-code SIM-001
```

Normal driving for exactly 30 seconds:

```bash
python sensor_simulator.py --device-code SIM-001 --scenario normal --duration 30
```

Trigger a severe crash (sharp accel + gyro spike partway through):

```bash
python sensor_simulator.py --device-code SIM-001 --scenario severe_crash --duration 30
```

Trigger a moderate impact:

```bash
python sensor_simulator.py --device-code SIM-001 --scenario moderate_impact --duration 30
```

Trigger a sustained gas leak (gradual ramp-up, stays elevated):

```bash
python sensor_simulator.py --device-code SIM-001 --scenario gas_leak --duration 60
```

Point at a non-default broker:

```bash
python sensor_simulator.py --device-code SIM-001 --broker-host 192.168.1.50 --broker-port 1883
```

Or configure the broker via `simulator/.env` instead of flags:

```
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
```

## Verifying it worked

While the simulator runs, check the backend's `uvicorn` terminal for log
lines like `Persisted sensor_reading id=... device_code=SIM-001`.

After running a `severe_crash` or `gas_leak` scenario, check for a new
incident:

```bash
curl http://localhost:8000/api/v1/incidents -H "Authorization: Bearer <token>"
```

You should see a new row with `incident_type: "accident"` (severe/moderate
scenarios) or `incident_type: "gas_leak"` (gas leak scenario), plus a
corresponding mock alert under `GET /api/v1/alerts`.

**If a crash/gas-leak scenario runs but no incident appears:** this
doesn't necessarily mean the simulator is broken — it means the values
this script publishes didn't cross whatever threshold the trained SVM/GMM
models (`ml/`) actually use. The spike magnitudes in `scenarios.py`
(`accel_spike_magnitude`, `gyro_spike_magnitude`, `peak_gas_level`) are
reasonable guesses, not tuned to the specific trained model. If incidents
aren't firing, try increasing those values in `scenarios.py`, or compare
them against the ranges used in `ml/data/synthetic_sensor_data.csv` /
`ml/training/generate_synthetic_data.py` to match what the models were
actually trained on.

## Testing an unknown device (negative case)

To confirm the simulator's payload shape is correct even when the backend
correctly rejects it:

```bash
python sensor_simulator.py --device-code DOES-NOT-EXIST --duration 5
```

Check the backend logs for `Dropped telemetry for unknown device_code=DOES-NOT-EXIST`
— that confirms the message was well-formed JSON matching the schema, and
was rejected only because the device isn't registered (correct behavior,
not a bug).

## What this script does NOT do

- No unit tests — it's a manual testing/exercising tool itself, not
  production code, per the sprint scope.
- Doesn't touch `backend/`, `frontend/`, or `ml/` — those are separate,
  already-implemented and verified.
- Doesn't modify `MQTT_SPEC.md`'s payload shape in any way.
