"""
Verification script for Sprint 2: Ambulance Dispatch
Executes end-to-end verification steps and outputs raw JSON responses.
"""
import asyncio
import sys
import time
import uuid
from datetime import datetime, timezone
import json

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import User, Device, Ambulance, Dispatch, Incident, SensorReading
from app.core.security import hash_password, create_access_token
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.hospital_service import haversine_distance


async def run_verification():
    print("=== SPRINT 2 VERIFICATION START ===")
    async with AsyncSessionLocal() as db:
        # 1. Ensure test admin user exists
        res = await db.execute(select(User).where(User.email == "admin@example.com"))
        admin = res.scalar_one_or_none()
        if not admin:
            admin = User(
                email="admin@example.com",
                hashed_password=hash_password("admin123"),
                full_name="System Admin",
                role="admin",
            )
            db.add(admin)
            await db.commit()
            await db.refresh(admin)

        token = create_access_token(str(admin.id))
        headers = {"Authorization": f"Bearer {token}"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:

            # STEP 2: Register 2 ambulances via API
            code_1 = f"AMB-VERIFY-001-{uuid.uuid4().hex[:4]}"
            code_2 = f"AMB-VERIFY-002-{uuid.uuid4().hex[:4]}"

            res1 = await client.post("/api/v1/ambulances", json={"ambulance_code": code_1, "label": "Downtown Patrol Unit"}, headers=headers)
            print("\n--- STEP 2: Register Ambulance 1 ---")
            print("Status Code:", res1.status_code)
            print("Response:", json.dumps(res1.json(), indent=2))

            res2 = await client.post("/api/v1/ambulances", json={"ambulance_code": code_2, "label": "Northside Rescue Unit"}, headers=headers)
            print("\n--- STEP 2: Register Ambulance 2 ---")
            print("Status Code:", res2.status_code)
            print("Response:", json.dumps(res2.json(), indent=2))

            amb1_id = res1.json()["id"]
            amb2_id = res2.json()["id"]

            # STEP 3: Simulate location updates over time (Timestamp 1 & Timestamp 2)
            # Update location at T1
            from app.services import ambulance_service
            amb1_obj = await ambulance_service.get_ambulance_by_id(db, uuid.UUID(amb1_id))
            amb2_obj = await ambulance_service.get_ambulance_by_id(db, uuid.UUID(amb2_id))

            t1 = datetime.now(timezone.utc)
            await ambulance_service.update_ambulance_location(db, amb1_obj, 12.9716, 77.5946, t1)
            await ambulance_service.update_ambulance_location(db, amb2_obj, 13.0500, 77.6200, t1)

            res_t1 = await client.get("/api/v1/ambulances", headers=headers)
            print("\n--- STEP 3: GET /ambulances at Timestamp 1 ---")
            print("Timestamp 1 Output:", json.dumps(res_t1.json(), indent=2))

            time.sleep(1)
            t2 = datetime.now(timezone.utc)
            await ambulance_service.update_ambulance_location(db, amb1_obj, 12.9722, 77.5952, t2)
            await ambulance_service.update_ambulance_location(db, amb2_obj, 13.0515, 77.6212, t2)

            res_t2 = await client.get("/api/v1/ambulances", headers=headers)
            print("\n--- STEP 3: GET /ambulances at Timestamp 2 (showing continuous movement) ---")
            print("Timestamp 2 Output:", json.dumps(res_t2.json(), indent=2))

            # STEP 4 & 5: Trigger severe crash near AMB-001 (12.9718, 77.5948)
            device = Device(device_code=f"SIM-CRASH-{uuid.uuid4().hex[:4]}", device_type="simulator")
            db.add(device)
            await db.commit()

            reading = SensorReading(
                device_id=device.id,
                accel_x=28.0,
                accel_y=12.0,
                accel_z=4.0,
                gas_level=180.0,
                latitude=12.9718,
                longitude=77.5948,
                recorded_at=datetime.now(timezone.utc),
            )
            db.add(reading)
            await db.commit()

            from app.ml.inference import run_inference
            from app.services import incident_service
            results = run_inference(
                accel_x=reading.accel_x, accel_y=reading.accel_y, accel_z=reading.accel_z,
                gyro_x=0.0, gyro_y=0.0, gyro_z=0.0, gas_level=reading.gas_level
            )
            incident = await incident_service.create_incident_from_inference(
                db, device_id=device.id, sensor_reading_id=reading.id,
                latitude=reading.latitude, longitude=reading.longitude, result=results[0]
            )

            print("\n--- STEP 4: Incident Created ---")
            print(f"Incident ID: {incident.id}, Type: {incident.incident_type}, Severity: {incident.severity}, Lat: {incident.latitude}, Lng: {incident.longitude}")

            # Nearest ambulances panel check
            res_nearest = await client.get(f"/api/v1/ambulances/nearest?lat={incident.latitude}&lng={incident.longitude}&limit=20", headers=headers)
            print("\n--- STEP 5: GET /ambulances/nearest for Incident Location ---")
            print("Nearest Ambulances Panel Output:", json.dumps(res_nearest.json()[:3], indent=2))
            codes = [item["ambulance_code"] for item in res_nearest.json()]
            assert code_1 in codes and code_2 in codes
            assert codes.index(code_1) < codes.index(code_2), "Expected closer ambulance code_1 before code_2"

            # STEP 6: Operator Dispatch Trigger
            res_dispatch = await client.post(
                f"/api/v1/incidents/{incident.id}/dispatch",
                json={"ambulance_id": amb1_id},
                headers=headers,
            )
            print("\n--- STEP 6: POST /incidents/{id}/dispatch ---")
            print("Dispatch Created Response:", json.dumps(res_dispatch.json(), indent=2))
            dispatch_id = res_dispatch.json()["id"]

            res_amb_dispatched = await client.get(f"/api/v1/ambulances/{amb1_id}", headers=headers)
            print("Ambulance Status After Dispatch:", res_amb_dispatched.json()["status"])
            assert res_amb_dispatched.json()["status"] == "dispatched"

            # STEP 7: Ambulance Tablet View Lifecycle (En Route -> Arrived -> Completed)
            print("\n--- STEP 7: Ambulance Tablet Status Progression ---")

            # Mark En Route
            res_enroute = await client.patch(f"/api/v1/dispatches/{dispatch_id}", json={"status": "en_route"}, headers=headers)
            print("1. PATCH status='en_route':", res_enroute.json()["status"])
            res_amb_enroute = await client.get(f"/api/v1/ambulances/{amb1_id}", headers=headers)
            print("   Ambulance Status:", res_amb_enroute.json()["status"])

            # Mark Arrived
            res_arrived = await client.patch(f"/api/v1/dispatches/{dispatch_id}", json={"status": "arrived"}, headers=headers)
            print("2. PATCH status='arrived':", res_arrived.json()["status"])
            res_amb_arrived = await client.get(f"/api/v1/ambulances/{amb1_id}", headers=headers)
            print("   Ambulance Status:", res_amb_arrived.json()["status"])

            # Mark Completed
            res_completed = await client.patch(f"/api/v1/dispatches/{dispatch_id}", json={"status": "completed"}, headers=headers)
            print("3. PATCH status='completed':", res_completed.json()["status"])
            res_amb_completed = await client.get(f"/api/v1/ambulances/{amb1_id}", headers=headers)
            print("   Ambulance Status Returned To:", res_amb_completed.json()["status"])
            assert res_amb_completed.json()["status"] == "available"

            print("\n=== ALL SPRINT 2 VERIFICATION STEPS PASSED PERFECTLY ===")


if __name__ == "__main__":
    asyncio.run(run_verification())
