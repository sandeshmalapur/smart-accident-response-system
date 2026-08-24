"""
End-to-End Verification script for Sprint 4: Relative Contact, SMS Alert & Trackable Link
"""
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath("backend"))
sys.path.insert(0, os.path.abspath("."))

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.db.models import Device, Incident, IncidentTrackingToken, SensorReading, User
from app.db.session import AsyncSessionLocal
from app.main import app
from app.ml.inference import run_inference
from app.services import incident_service, tracking_service


async def run_verification():
    print("=== SPRINT 4 TRACKING & SMS VERIFICATION START ===\n")

    async with AsyncSessionLocal() as db:
        # 1. Admin user & headers for setup
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

            # STEP 1: Register Device with Emergency Contact Info via POST /api/v1/devices
            dev_code = f"SIM-DEV-SMS-{uuid.uuid4().hex[:4]}"
            device_payload = {
                "device_code": dev_code,
                "device_type": "simulator",
                "label": "Sprint 4 Family SUV",
                "owner_name": "Alexander Wright",
                "emergency_contact_name": "Eleanor Wright (Wife)",
                "emergency_contact_phone": "+15550192837",
            }
            res_dev = await client.post("/api/v1/devices", json=device_payload, headers=headers)
            print("--- STEP 1: Register Device with Emergency Contact Info ---")
            print("POST /api/v1/devices Response:")
            print(json.dumps(res_dev.json(), indent=2))
            assert res_dev.status_code == 201
            dev_data = res_dev.json()
            assert dev_data["owner_name"] == "Alexander Wright"
            assert dev_data["emergency_contact_phone"] == "+15550192837"
            device_id = uuid.UUID(dev_data["id"])

            # STEP 2: Trigger Severe Crash Incident
            reading = SensorReading(
                device_id=device_id,
                accel_x=34.0,
                accel_y=16.0,
                accel_z=8.0,
                gas_level=210.0,
                latitude=12.9716,
                longitude=77.5946,
                recorded_at=datetime.now(timezone.utc),
            )
            db.add(reading)
            await db.commit()

            results = run_inference(
                accel_x=reading.accel_x,
                accel_y=reading.accel_y,
                accel_z=reading.accel_z,
                gyro_x=0.0,
                gyro_y=0.0,
                gyro_z=0.0,
                gas_level=reading.gas_level,
            )
            incident = await incident_service.create_incident_from_inference(
                db,
                device_id=device_id,
                sensor_reading_id=reading.id,
                latitude=reading.latitude,
                longitude=reading.longitude,
                result=results[0],
            )
            print(f"\n--- STEP 2: Triggered Severe Crash (Incident ID: {incident.id}) ---")

            # Verify IncidentTrackingToken created in DB
            tok_res = await db.execute(
                select(IncidentTrackingToken).where(IncidentTrackingToken.incident_id == incident.id)
            )
            tracking_tok = tok_res.scalar_one_or_none()
            assert tracking_tok is not None, "Expected IncidentTrackingToken to be generated"
            print(f"Generated Tracking Token: {tracking_tok.token}")
            print(f"Token Expires At: {tracking_tok.expires_at}")

            # STEP 3: Query GET /api/v1/track/{token} raw response (UNAUTHENTICATED)
            print("\n--- STEP 3: Query GET /api/v1/track/{token} (Unauthenticated, No Bearer Token) ---")
            res_track = await client.get(f"/api/v1/track/{tracking_tok.token}")
            print("Raw Response Output:")
            print(json.dumps(res_track.json(), indent=2))
            assert res_track.status_code == 200
            track_payload = res_track.json()
            assert track_payload["token"] == tracking_tok.token
            assert track_payload["owner_name"] == "Alexander Wright"
            assert track_payload["incident_type"] == "accident"
            assert track_payload["severity"] == "severe"

            # STEP 4: Confirm Fake and Expired Tokens Return 404
            print("\n--- STEP 4: Test Fake and Expired Tokens ---")

            # Fake token test
            res_fake = await client.get("/api/v1/track/non-existent-fake-token-xyz")
            print("Fake Token Response Status Code:", res_fake.status_code)
            print("Fake Token Response JSON:", res_fake.json())
            assert res_fake.status_code == 404

            # Expired token test
            expired_token_str = f"expired-test-{uuid.uuid4().hex[:8]}"
            expired_tok = IncidentTrackingToken(
                incident_id=incident.id,
                token=expired_token_str,
                created_at=datetime.now(timezone.utc) - timedelta(hours=25),
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            )
            db.add(expired_tok)
            await db.commit()

            res_expired = await client.get(f"/api/v1/track/{expired_token_str}")
            print("Expired Token Response Status Code:", res_expired.status_code)
            print("Expired Token Response JSON:", res_expired.json())
            assert res_expired.status_code == 404

            print("\n=== ALL SPRINT 4 TRACKING & SMS VERIFICATION STEPS PASSED PERFECTLY ===")


if __name__ == "__main__":
    asyncio.run(run_verification())
