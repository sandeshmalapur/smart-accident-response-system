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

        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
