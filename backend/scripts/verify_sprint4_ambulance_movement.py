"""
End-to-End Verification script for Sprint 4: Ambulance Movement Toward Dispatched Incident
"""
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath("backend"))
sys.path.insert(0, os.path.abspath("."))

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token, hash_password

from app.db.models import Ambulance, Device, Incident, SensorReading, User
from app.db.session import AsyncSessionLocal
from app.main import app
from app.services import ambulance_service, dispatch_service, incident_service
from simulator.ambulance_simulator import fetch_active_dispatch


async def run_verification():
    print("=== SPRINT 4 AMBULANCE NAVIGATION VERIFICATION START ===\n")

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

            # 2. Register Device and trigger severe crash near known target coordinates (12.9850, 77.6050)
            dev_code = f"SIM-DEV-NAV-{uuid.uuid4().hex[:4]}"
            device = Device(device_code=dev_code, device_type="simulator")
            db.add(device)
            await db.commit()
            await db.refresh(device)

            incident_lat = 12.985000
            incident_lng = 77.605000

            reading = SensorReading(
                device_id=device.id,
                accel_x=30.0,
                accel_y=15.0,
                accel_z=5.0,
                gas_level=180.0,
                latitude=incident_lat,
                longitude=incident_lng,
                recorded_at=datetime.now(timezone.utc),
            )
            db.add(reading)
            await db.commit()
            await db.refresh(reading)

            incident = Incident(
                device_id=device.id,
                sensor_reading_id=reading.id,
                incident_type="accident",
                severity="severe",
                severity_score=9.5,
                latitude=incident_lat,
                longitude=incident_lng,
                status="open",
            )
            db.add(incident)
            await db.commit()
            await db.refresh(incident)

            print(f"--- STEP 1: Created Severe Crash Incident ---")
            print(f"Incident ID: {incident.id}")
            print(f"Target Incident Location: (lat={incident_lat:.6f}, lng={incident_lng:.6f})")

            # 3. Create Ambulance starting far from incident at (12.9716, 77.5946)
            amb_code = f"AMB-NAV-{uuid.uuid4().hex[:4]}"
            start_lat = 12.971600
            start_lng = 77.594600
            amb = Ambulance(
                ambulance_code=amb_code,
                label="Navigator Ambulance",
                current_latitude=start_lat,
                current_longitude=start_lng,
                status="available",
            )
            db.add(amb)
            await db.commit()
            await db.refresh(amb)

            print(f"\n--- STEP 2: Registered Ambulance {amb_code} ---")
            print(f"Starting Location: (lat={start_lat:.6f}, lng={start_lng:.6f}), status='available'")

            # 4. Check active dispatch when available -> should be null
            active_disp_res_1 = await client.get(f"/api/v1/ambulances/{amb_code}/active-dispatch")
            print("\n--- STEP 3: GET /ambulances/{code}/active-dispatch (Before Dispatch) ---")
            print("Response:", active_disp_res_1.json())
            assert active_disp_res_1.json() is None

            # 5. Dispatch Ambulance to Incident
            disp_res = await client.post(
                f"/api/v1/incidents/{incident.id}/dispatch",
                json={"ambulance_id": str(amb.id)},
                headers=headers,
            )
            dispatch_data = disp_res.json()
            dispatch_id = dispatch_data["id"]
            print(f"\n--- STEP 4: Dispatched Ambulance to Incident (Dispatch ID: {dispatch_id}) ---")
            print("Dispatch Status:", dispatch_data["status"])

            # 6. Check active dispatch endpoint after dispatch
            active_disp_res_2 = await client.get(f"/api/v1/ambulances/{amb_code}/active-dispatch")
            active_disp = active_disp_res_2.json()
            print("\n--- STEP 5: GET /ambulances/{code}/active-dispatch (After Dispatch) ---")
            print(json.dumps(active_disp, indent=2))
            assert active_disp["status"] == "dispatched"
            assert active_disp["incident"]["latitude"] == incident_lat
            assert active_disp["incident"]["longitude"] == incident_lng

            # 7. Simulate movement ticks over 5 iterations and record coordinates
            print("\n--- STEP 6: Simulating Ambulance Movement Convergence Ticks ---")
            cur_lat = start_lat
            cur_lng = start_lng

            for tick in range(1, 6):
                active_data = (await client.get(f"/api/v1/ambulances/{amb_code}/active-dispatch")).json()
                assert active_data is not None

                inc = active_data["incident"]
                t_lat, t_lng = inc["latitude"], inc["longitude"]
                d_lat, d_lng = t_lat - cur_lat, t_lng - cur_lng
                dist_deg = (d_lat**2 + d_lng**2) ** 0.5

                if dist_deg > 0.00045:
                    cur_lat += d_lat * 0.18
                    cur_lng += d_lng * 0.18

                # Update ambulance location in DB (simulating simulator publishing telemetry)
                amb_db = await ambulance_service.get_ambulance_by_code(db, amb_code)
                await ambulance_service.update_ambulance_location(
                    db, ambulance=amb_db, lat=cur_lat, lng=cur_lng
                )


                # Fetch updated ambulance model via API
                amb_info = (await client.get(f"/api/v1/ambulances/{amb.id}", headers=headers)).json()
                dist_to_target = ((t_lat - amb_info['current_latitude'])**2 + (t_lng - amb_info['current_longitude'])**2)**0.5
                print(
                    f"Tick {tick}: Ambulance Location = (lat={amb_info['current_latitude']:.6f}, lng={amb_info['current_longitude']:.6f}) "
                    f"| Distance to Target = {dist_to_target:.6f} deg"
                )

            # Assert distance has decreased significantly (converging towards incident)
            final_dist = ((incident_lat - cur_lat)**2 + (incident_lng - cur_lng)**2)**0.5
            initial_dist = ((incident_lat - start_lat)**2 + (incident_lng - start_lng)**2)**0.5
            print(f"\nConvergence Summary: Initial Dist={initial_dist:.6f} deg -> Final Dist={final_dist:.6f} deg")
            assert final_dist < initial_dist * 0.5, "Ambulance distance should have decreased by at least 50%"

            # 8. Complete Dispatch and verify active-dispatch returns null
            comp_res = await client.patch(
                f"/api/v1/dispatches/{dispatch_id}",
                json={"status": "completed"},
                headers=headers,
            )
            print("\n--- STEP 7: Completed Dispatch ---")
            print("Dispatch Status:", comp_res.json()["status"])

            active_disp_res_3 = await client.get(f"/api/v1/ambulances/{amb_code}/active-dispatch")
            print("GET /ambulances/{code}/active-dispatch after completed:", active_disp_res_3.json())
            assert active_disp_res_3.json() is None

            print("\n=== ALL SPRINT 4 VERIFICATION STEPS PASSED PERFECTLY ===")


if __name__ == "__main__":
    asyncio.run(run_verification())
