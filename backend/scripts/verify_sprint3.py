"""
End-to-End Verification script for Sprint 3: Victim Welfare Check & Escalation
"""
import asyncio
import json
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core import welfare_messages
from app.core.security import create_access_token, hash_password
from app.db.models import Device, Incident, SensorReading, User, WelfareCheck
from app.db.session import AsyncSessionLocal
from app.main import app
from app.ml.inference import run_inference
from app.schemas.welfare_check import WelfareCheckOut
from app.services import incident_service, welfare_check_service


async def run_verification():
    print("=== SPRINT 3 VERIFICATION START ===")

    # 1. Audit welfare_messages.py contents
    print("\n--- STEP 1: Audit welfare_messages.py File Contents ---")
    with open("app/core/welfare_messages.py", "r", encoding="utf-8") as f:
        content = f.read()
    print(content)

    async with AsyncSessionLocal() as db:
        # Ensure test admin user exists
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

            # STEP 2: Trigger severe crash and verify auto-created welfare_check
            dev_code_1 = f"SIM-DEV-WC1-{uuid.uuid4().hex[:4]}"
            device_1 = Device(device_code=dev_code_1, device_type="simulator")
            db.add(device_1)
            await db.commit()
            await db.refresh(device_1)

            reading_1 = SensorReading(
                device_id=device_1.id,
                accel_x=28.0,
                accel_y=12.0,
                accel_z=4.0,
                gas_level=180.0,
                latitude=12.9716,
                longitude=77.5946,
                recorded_at=datetime.now(timezone.utc),
            )
            db.add(reading_1)
            await db.commit()

            results_1 = run_inference(
                accel_x=reading_1.accel_x, accel_y=reading_1.accel_y, accel_z=reading_1.accel_z,
                gyro_x=0.0, gyro_y=0.0, gyro_z=0.0, gas_level=reading_1.gas_level
            )
            incident_1 = await incident_service.create_incident_from_inference(
                db, device_id=device_1.id, sensor_reading_id=reading_1.id,
                latitude=reading_1.latitude, longitude=reading_1.longitude, result=results_1[0]
            )

            print(f"\n--- STEP 2: Triggered Severe Crash Incident (ID: {incident_1.id}) ---")

            res_wc_list = await client.get(f"/api/v1/welfare-checks?incident_id={incident_1.id}", headers=headers)
            print("GET /api/v1/welfare-checks?incident_id=... Response:")
            print(json.dumps(res_wc_list.json(), indent=2))
            assert len(res_wc_list.json()) == 1, "Expected 1 auto-created welfare_check"
            wc_1_id = res_wc_list.json()[0]["id"]
            assert res_wc_list.json()[0]["status"] == "awaiting_response"

            # STEP 3: In-vehicle screen poll & respond "ok"
            print(f"\n--- STEP 3: Vehicle Screen (/vehicle/{dev_code_1}) Poll & Response ---")
            res_device_wc = await client.get(f"/api/v1/welfare-checks/device/{dev_code_1}")
            print("GET /api/v1/welfare-checks/device/{device_code} Output:")
            print(json.dumps(res_device_wc.json(), indent=2))
            assert res_device_wc.json()["prompt"] == welfare_messages.WELFARE_CHECK_PROMPT

            res_respond = await client.post(f"/api/v1/welfare-checks/{wc_1_id}/respond", json={"response": "ok"})
            print("POST /api/v1/welfare-checks/{id}/respond Output:")
            print(json.dumps(res_respond.json(), indent=2))
            assert res_respond.json()["status"] == "responded_ok"
            assert res_respond.json()["safety_guidance"] == welfare_messages.SAFETY_GUIDANCE

            # STEP 4: Trigger second severe crash and test timeout escalation
            dev_code_2 = f"SIM-DEV-WC2-{uuid.uuid4().hex[:4]}"
            device_2 = Device(device_code=dev_code_2, device_type="simulator")
            db.add(device_2)
            await db.commit()
            await db.refresh(device_2)

            reading_2 = SensorReading(
                device_id=device_2.id,
                accel_x=30.0,
                accel_y=15.0,
                accel_z=5.0,
                gas_level=180.0,
                latitude=12.9800,
                longitude=77.6000,
                recorded_at=datetime.now(timezone.utc),
            )
            db.add(reading_2)
            await db.commit()

            results_2 = run_inference(
                accel_x=reading_2.accel_x, accel_y=reading_2.accel_y, accel_z=reading_2.accel_z,
                gyro_x=0.0, gyro_y=0.0, gyro_z=0.0, gas_level=reading_2.gas_level
            )
            incident_2 = await incident_service.create_incident_from_inference(
                db, device_id=device_2.id, sensor_reading_id=reading_2.id,
                latitude=reading_2.latitude, longitude=reading_2.longitude, result=results_2[0]
            )

            print(f"\n--- STEP 4: Triggered 2nd Severe Crash (ID: {incident_2.id}) For Timeout Test ---")
            res_wc2_list = await client.get(f"/api/v1/welfare-checks?incident_id={incident_2.id}", headers=headers)
            wc_2 = await welfare_check_service.get_welfare_check_by_id(db, uuid.UUID(res_wc2_list.json()[0]["id"]))
            
            # Backdate initiated_at to 100 seconds ago
            wc_2.initiated_at = datetime.now(timezone.utc) - timedelta(seconds=100)
            await db.commit()

            escalated = await welfare_check_service.escalate_expired_welfare_checks(db, timeout_seconds=90.0)
            print(f"Escalated {len(escalated)} expired check(s).")

            res_wc2_after = await client.get(f"/api/v1/welfare-checks/{wc_2.id}", headers=headers)
            print("GET /api/v1/welfare-checks/{id} After Escalation Timeout:")
            print(json.dumps(res_wc2_after.json(), indent=2))
            assert res_wc2_after.json()["status"] == "no_response_escalated"
            assert res_wc2_after.json()["escalation_notice"] == welfare_messages.ESCALATION_NOTICE

            print("\n=== ALL SPRINT 3 VERIFICATION STEPS PASSED PERFECTLY ===")


if __name__ == "__main__":
    asyncio.run(run_verification())
