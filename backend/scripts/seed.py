"""
Seed script for local dev — STRICTLY Bengaluru Only.

Usage (from backend/):
    python -m scripts.seed

Creates / Resets:
- Admin test user (email: admin@example.com / password: changeme123)
- Simulator device (device_code: SIM-001)
- 4 Designated Trauma Hospitals across Bengaluru
- 5 Stationed Emergency Ambulances (AMB-001 to AMB-005) all 'available'
- 4 Multi-Agency Police & Fire units (POL-001, POL-002, FIRE-001, FIRE-002)
- 5 Realistic Open Crash & Gas Incidents on real Bengaluru roads (MG Road, Indiranagar, Koramangala, Hebbal, Residency Road)
- Purges any non-Bengaluru rows or temporary mock units outside Bangalore bounds.
"""
import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.core.security import hash_password
from app.db.models import (
    AgencyDispatch,
    AgencyUnit,
    Alert,
    Ambulance,
    Device,
    Dispatch,
    Hospital,
    Incident,
    IncidentTrackingToken,
    SensorReading,
    User,
    WelfareCheck,
)
from app.db.session import AsyncSessionLocal

TEST_ADMIN_EMAIL = "admin@example.com"
TEST_ADMIN_PASSWORD = "changeme123"
TEST_DEVICE_CODE = "SIM-001"

# Bengaluru bounding box
BLR_LAT_MIN, BLR_LAT_MAX = 12.80, 13.15
BLR_LNG_MIN, BLR_LNG_MAX = 77.45, 77.78


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        print("--- Cleaning non-Bengaluru or orphaned demo data ---")

        # 1. Purge non-Bengaluru incidents and dispatches
        all_incs = (await db.execute(select(Incident))).scalars().all()
        for inc in all_incs:
            if not (BLR_LAT_MIN <= inc.latitude <= BLR_LAT_MAX and BLR_LNG_MIN <= inc.longitude <= BLR_LNG_MAX):
                print(f"Purging non-Bengaluru incident {inc.id} at ({inc.latitude}, {inc.longitude})")
                await db.execute(delete(IncidentTrackingToken).where(IncidentTrackingToken.incident_id == inc.id))
                await db.execute(delete(WelfareCheck).where(WelfareCheck.incident_id == inc.id))
                await db.execute(delete(Alert).where(Alert.incident_id == inc.id))
                await db.execute(delete(AgencyDispatch).where(AgencyDispatch.incident_id == inc.id))
                await db.execute(delete(Dispatch).where(Dispatch.incident_id == inc.id))
                await db.execute(delete(Incident).where(Incident.id == inc.id))

        # 2. Purge test ambulances (AMB-TEST-*, AMB-FAR-*, AMB-IDLE-*, AMB-NAV-*, AMB-NEAR-*, or coordinates=None)
        all_ambs = (await db.execute(select(Ambulance))).scalars().all()
        allowed_amb_codes = {"AMB-001", "AMB-002", "AMB-003", "AMB-004", "AMB-005"}
        for amb in all_ambs:
            if amb.ambulance_code not in allowed_amb_codes or amb.current_latitude is None or amb.current_longitude is None:
                print(f"Purging extra/mock ambulance {amb.ambulance_code}")
                await db.execute(delete(Dispatch).where(Dispatch.ambulance_id == amb.id))
                await db.execute(delete(Ambulance).where(Ambulance.id == amb.id))

        # 3. Clean any existing active dispatches so all ambulances are fresh & available
        await db.execute(delete(Dispatch))
        await db.execute(delete(AgencyDispatch))
        await db.commit()

        # 4. User
        res = await db.execute(select(User).where(User.email == TEST_ADMIN_EMAIL))
        user = res.scalar_one_or_none()
        if user is None:
            user = User(
                email=TEST_ADMIN_EMAIL,
                hashed_password=hash_password(TEST_ADMIN_PASSWORD),
                full_name="Bengaluru Central Dispatcher",
                role="admin",
            )
            db.add(user)
            await db.commit()
            print(f"Created admin user {TEST_ADMIN_EMAIL} / {TEST_ADMIN_PASSWORD}")
        else:
            print(f"Admin user {TEST_ADMIN_EMAIL} ready")

        # 5. Device
        res = await db.execute(select(Device).where(Device.device_code == TEST_DEVICE_CODE))
        device = res.scalar_one_or_none()
        if device is None:
            device = Device(
                device_code=TEST_DEVICE_CODE,
                device_type="simulator",
                label="Bengaluru Telemetry Node 1",
                owner_name="Karnataka Transport Safety",
                emergency_contact_phone="+91 98800 12345",
                is_active=True,
            )
            db.add(device)
            await db.commit()
            await db.refresh(device)
            print(f"Created device {TEST_DEVICE_CODE}")
        else:
            device.is_active = True
            await db.commit()
            await db.refresh(device)
            print(f"Device {TEST_DEVICE_CODE} ready")

        # 6. Bengaluru Hospitals
        hospitals_data = [
            ("Victoria Hospital Trauma Care", 12.9620, 77.5750, "+91 80 2670 1150"),
            ("Manipal Emergency Facility - Old Airport Rd", 12.9580, 77.6410, "+91 80 2502 4444"),
            ("Bowring & Lady Curzon Hospital", 12.9822, 77.6033, "+91 80 2559 1362"),
            ("Fortis Emergency Hospital - Bannerghatta", 12.8948, 77.5982, "+91 80 6621 4444"),
        ]
        created_hospitals: list[Hospital] = []
        for name, lat, lng, phone in hospitals_data:
            h_res = await db.execute(select(Hospital).where(Hospital.name == name))
            h = h_res.scalar_one_or_none()
            if h is None:
                h = Hospital(name=name, latitude=lat, longitude=lng, phone=phone, is_active=True)
                db.add(h)
                await db.commit()
                await db.refresh(h)
                print(f"Created Hospital: {name} at ({lat}, {lng})")
            else:
                h.latitude = lat
                h.longitude = lng
                h.phone = phone
                h.is_active = True
                await db.commit()
            created_hospitals.append(h)

        # 7. Bengaluru Ambulances (5 strategically stationed units)
        now = datetime.now(timezone.utc)
        ambulance_specs = [
            ("AMB-001", "MG Road Rapid Response ALS", 12.9740, 77.5920),
            ("AMB-002", "Victoria Hospital Trauma Unit", 12.9640, 77.5760),
            ("AMB-003", "Manipal Advanced Life Support", 12.9560, 77.6380),
            ("AMB-004", "Koramangala City ALS Unit", 12.9340, 77.6180),
            ("AMB-005", "Hebbal Expressway Rescue ALS", 13.0320, 77.5940),
        ]
        for code, label, lat, lng in ambulance_specs:
            res = await db.execute(select(Ambulance).where(Ambulance.ambulance_code == code))
            amb = res.scalar_one_or_none()
            if amb is None:
                amb = Ambulance(
                    ambulance_code=code,
                    label=label,
                    current_latitude=lat,
                    current_longitude=lng,
                    status="available",
                    last_location_update=now,
                )
                db.add(amb)
                print(f"Created Ambulance {code} ({label}) at ({lat}, {lng})")
            else:
                amb.label = label
                amb.current_latitude = lat
                amb.current_longitude = lng
                amb.status = "available"
                amb.last_location_update = now
                print(f"Reset Ambulance {code} to 'available' at ({lat}, {lng})")
        await db.commit()

        # 8. Bengaluru Police & Fire Agency Units
        agency_specs = [
            ("police", "POL-001", "Cubbon Park Central Police Patrol", "+91 80 2222 1000", 12.9770, 77.5950),
            ("police", "POL-002", "Koramangala Traffic Emergency Patrol", "+91 80 2553 2000", 12.9360, 77.6260),
            ("fire", "FIRE-001", "High Grounds Fire & Rescue Station", "+91 80 2222 1010", 12.9880, 77.5870),
            ("fire", "FIRE-002", "Jayanagar Metro Fire Station", "+91 80 2656 1010", 12.9280, 77.5850),
        ]
        for utype, code, label, phone, lat, lng in agency_specs:
            res = await db.execute(select(AgencyUnit).where(AgencyUnit.unit_code == code))
            unit = res.scalar_one_or_none()
            if unit is None:
                unit = AgencyUnit(
                    agency_type=utype,
                    unit_code=code,
                    label=label,
                    contact_phone=phone,
                    current_latitude=lat,
                    current_longitude=lng,
                    status="available",
                    last_location_update=now,
                )
                db.add(unit)
                print(f"Created Agency Unit {code} ({label}) at ({lat}, {lng})")
            else:
                unit.label = label
                unit.current_latitude = lat
                unit.current_longitude = lng
                unit.status = "available"
                unit.last_location_update = now
                print(f"Reset Agency Unit {code} to 'available' at ({lat}, {lng})")
        await db.commit()

        # 9. Clean & Seed 5 Bengaluru Incidents with attached SensorReadings
        # First remove any previous seeded incidents to guarantee fresh, clean state
        existing_incs = (await db.execute(select(Incident))).scalars().all()
        for inc in existing_incs:
            await db.execute(delete(IncidentTrackingToken).where(IncidentTrackingToken.incident_id == inc.id))
            await db.execute(delete(WelfareCheck).where(WelfareCheck.incident_id == inc.id))
            await db.execute(delete(Alert).where(Alert.incident_id == inc.id))
            await db.execute(delete(Dispatch).where(Dispatch.incident_id == inc.id))
            await db.execute(delete(AgencyDispatch).where(AgencyDispatch.incident_id == inc.id))
            await db.execute(delete(Incident).where(Incident.id == inc.id))
        await db.commit()

        bengaluru_incidents_data = [
            {
                "title": "Severe Crash - MG Road Trinity Junction",
                "type": "accident",
                "severity": "severe",
                "severity_score": 0.96,
                "anomaly_score": 3.12,
                "lat": 12.9756,
                "lng": 77.6080,
                "gas": 42.0,
                "accel": (3.4, 2.8, 1.2),
                "hosp_idx": 0,
            },
            {
                "title": "Multi-Vehicle Collision - Indiranagar 100ft Road",
                "type": "accident",
                "severity": "severe",
                "severity_score": 0.91,
                "anomaly_score": 2.85,
                "lat": 12.9719,
                "lng": 77.6412,
                "gas": 38.0,
                "accel": (2.9, 3.1, 0.9),
                "hosp_idx": 1,
            },
            {
                "title": "Two-Wheeler Impact - Koramangala Sony World Signal",
                "type": "accident",
                "severity": "moderate",
                "severity_score": 0.78,
                "anomaly_score": 2.10,
                "lat": 12.9352,
                "lng": 77.6245,
                "gas": 45.0,
                "accel": (2.1, 1.9, 0.6),
                "hosp_idx": 1,
            },
            {
                "title": "High-Speed Collision - Hebbal Flyover Bellary Rd",
                "type": "accident",
                "severity": "severe",
                "severity_score": 0.98,
                "anomaly_score": 3.45,
                "lat": 13.0358,
                "lng": 77.5970,
                "gas": 50.0,
                "accel": (4.1, 3.2, 1.5),
                "hosp_idx": 2,
            },
            {
                "title": "Hazardous Gas Leak - Residency Road Commercial Zone",
                "type": "gas_leak",
                "severity": "severe",
                "severity_score": 0.92,
                "anomaly_score": 3.20,
                "lat": 12.9698,
                "lng": 77.6025,
                "gas": 820.0,
                "accel": (0.1, 0.1, 1.0),
                "hosp_idx": 0,
            },
        ]

        for item in bengaluru_incidents_data:
            reading = SensorReading(
                device_id=device.id,
                accel_x=item["accel"][0],
                accel_y=item["accel"][1],
                accel_z=item["accel"][2],
                gas_level=item["gas"],
                latitude=item["lat"],
                longitude=item["lng"],
                recorded_at=now,
            )
            db.add(reading)
            await db.commit()
            await db.refresh(reading)

            nearest_hosp = created_hospitals[item["hosp_idx"]]

            incident = Incident(
                device_id=device.id,
                sensor_reading_id=reading.id,
                nearest_hospital_id=nearest_hosp.id,
                incident_type=item["type"],
                severity=item["severity"],
                severity_score=item["severity_score"],
                anomaly_score=item["anomaly_score"],
                latitude=item["lat"],
                longitude=item["lng"],
                status="open",
                created_at=now,
            )
            db.add(incident)
            await db.commit()
            await db.refresh(incident)

            alert = Alert(
                incident_id=incident.id,
                channel="mock",
                recipient="+91 80 2222 3333",
                payload={"message": f"CRITICAL: {item['title']} requires immediate response dispatch."},
                delivery_status="sent",
                dispatched_at=now,
            )
            db.add(alert)
            await db.commit()

            print(f"Seeded Bengaluru Incident: {item['title']} at ({item['lat']}, {item['lng']}) - id={incident.id}")

        print("=== Bengaluru Seeding Complete Successfully! ===")


if __name__ == "__main__":
    asyncio.run(seed())
