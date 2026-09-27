"""
Seed script for local dev.

Usage (from backend/):
    python -m scripts.seed

Creates:
- one admin test user (email: admin@example.com / password: changeme123)
- one simulator device (device_code: SIM-001), so mosquitto_pub tests against
  safe/SIM-001/telemetry resolve to a real device_id.

Idempotent: safe to re-run, skips rows that already exist.
"""
import asyncio

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import Device, User
from app.db.session import AsyncSessionLocal

TEST_ADMIN_EMAIL = "admin@example.com"
TEST_ADMIN_PASSWORD = "changeme123"
TEST_DEVICE_CODE = "SIM-001"


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == TEST_ADMIN_EMAIL))
        if result.scalar_one_or_none() is None:
            db.add(
                User(
                    email=TEST_ADMIN_EMAIL,
                    hashed_password=hash_password(TEST_ADMIN_PASSWORD),
                    full_name="Test Admin",
                    role="admin",
                )
            )
            print(f"Created user {TEST_ADMIN_EMAIL} / {TEST_ADMIN_PASSWORD}")
        else:
            print(f"User {TEST_ADMIN_EMAIL} already exists, skipping")

        result = await db.execute(select(Device).where(Device.device_code == TEST_DEVICE_CODE))
        if result.scalar_one_or_none() is None:
            db.add(Device(device_code=TEST_DEVICE_CODE, device_type="simulator", label="Seed Test Vehicle"))
            print(f"Created device {TEST_DEVICE_CODE}")
        else:
            print(f"Device {TEST_DEVICE_CODE} already exists, skipping")

        from app.db.models import Hospital
        hosp_result = await db.execute(select(Hospital))
        if not hosp_result.scalars().first():
            hospitals = [
                Hospital(
                    name="Bangalore Emergency Medical Center",
                    latitude=12.9716,
                    longitude=77.5946,
                    phone="+91 80 2222 3333",
                ),
                Hospital(
                    name="Victoria Hospital Trauma Care",
                    latitude=12.9620,
                    longitude=77.5750,
                    phone="+91 80 2670 1150",
                ),
                Hospital(
                    name="Manipal Emergency Facility",
                    latitude=12.9580,
                    longitude=77.6410,
                    phone="+91 80 2502 4444",
                ),
            ]
            db.add_all(hospitals)
            print("Created default sample hospitals")

        from datetime import datetime, timezone
        from app.db.models import Ambulance
        now = datetime.now(timezone.utc)
        ambulance_specs = [
            ("AMB-001", "City Central Rapid Response", 12.9740, 77.5920),
            ("AMB-002", "Victoria Trauma Unit", 12.9650, 77.5780),
            ("AMB-003", "Manipal Advanced Life Support", 12.9560, 77.6380),
        ]
        for code, label, lat, lng in ambulance_specs:
            res = await db.execute(select(Ambulance).where(Ambulance.ambulance_code == code))
            amb = res.scalar_one_or_none()
            if amb is None:
                db.add(
                    Ambulance(
                        ambulance_code=code,
                        label=label,
                        current_latitude=lat,
                        current_longitude=lng,
                        status="available",
                        last_location_update=now,
                    )
                )
                print(f"Created ambulance {code} ({label}) at ({lat}, {lng})")
            else:
                amb.current_latitude = lat
                amb.current_longitude = lng
                amb.last_location_update = now
                print(f"Updated ambulance {code} coordinates to ({lat}, {lng})")

        from app.db.models import AgencyUnit
        agency_specs = [
            ("police", "POL-001", "Central Police Patrol 1", "+91 80 2222 1000", 12.9780, 77.5850),
            ("fire", "FIRE-001", "Metro Fire & Rescue Unit 1", "+91 80 2222 1010", 12.9610, 77.6020),
        ]
        for utype, code, label, phone, lat, lng in agency_specs:
            res = await db.execute(select(AgencyUnit).where(AgencyUnit.unit_code == code))
            unit = res.scalar_one_or_none()
            if unit is None:
                db.add(
                    AgencyUnit(
                        agency_type=utype,
                        unit_code=code,
                        label=label,
                        contact_phone=phone,
                        current_latitude=lat,
                        current_longitude=lng,
                        status="available",
                        last_location_update=now,
                    )
                )
                print(f"Created agency unit {code} ({label}) at ({lat}, {lng})")
            else:
                unit.current_latitude = lat
                unit.current_longitude = lng
                unit.last_location_update = now
                print(f"Updated agency unit {code} coordinates to ({lat}, {lng})")

        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
