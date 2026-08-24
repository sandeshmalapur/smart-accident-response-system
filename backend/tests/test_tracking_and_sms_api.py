import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.db.models import Device, Incident, IncidentTrackingToken, SensorReading, User
from app.ml.inference import run_inference
from app.services import incident_service, tracking_service


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        hashed_password=hash_password("adminpassword123"),
        full_name="Admin User",
        role="admin",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_device_creation_with_emergency_contacts(client: AsyncClient, admin_user: User):
    token = create_access_token(str(admin_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    dev_code = f"DEV-CONTACT-{uuid.uuid4().hex[:4]}"
    res = await client.post(
        "/api/v1/devices",
        json={
            "device_code": dev_code,
            "device_type": "simulator",
            "label": "Family Sedan",
            "owner_name": "Alice Smith",
            "emergency_contact_name": "Bob Smith",
            "emergency_contact_phone": "+15551234567",
        },
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["device_code"] == dev_code
    assert data["owner_name"] == "Alice Smith"
    assert data["emergency_contact_name"] == "Bob Smith"
    assert data["emergency_contact_phone"] == "+15551234567"


@pytest.mark.asyncio
async def test_severe_crash_triggers_tracking_token_and_public_endpoint(
    client: AsyncClient, db_session: AsyncSession
):
    # 1. Register device with emergency contact
    dev_code = f"SIM-DEV-TRACK-{uuid.uuid4().hex[:4]}"
    device = Device(
        device_code=dev_code,
        device_type="simulator",
        owner_name="Charlie Brown",
        emergency_contact_name="Sally Brown",
        emergency_contact_phone="+15559876543",
    )
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)

    # 2. Trigger severe crash
    reading = SensorReading(
        device_id=device.id,
        accel_x=32.0,
        accel_y=14.0,
        accel_z=6.0,
        gas_level=190.0,
        latitude=12.9716,
        longitude=77.5946,
        recorded_at=datetime.now(timezone.utc),
    )
    db_session.add(reading)
    await db_session.commit()

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
        db_session,
        device_id=device.id,
        sensor_reading_id=reading.id,
        latitude=reading.latitude,
        longitude=reading.longitude,
        result=results[0],
    )
    assert incident.severity == "severe"

    # 3. Verify IncidentTrackingToken created in DB
    tok_res = await db_session.execute(
        select(IncidentTrackingToken).where(IncidentTrackingToken.incident_id == incident.id)
    )
    tracking_token = tok_res.scalar_one_or_none()
    assert tracking_token is not None
    assert len(tracking_token.token) > 20

    # 4. Query public tracking endpoint WITHOUT auth header
    res = await client.get(f"/api/v1/track/{tracking_token.token}")
    assert res.status_code == 200
    track_data = res.json()
    assert track_data["token"] == tracking_token.token
    assert track_data["owner_name"] == "Charlie Brown"
    assert track_data["incident_type"] == "accident"
    assert track_data["severity"] == "severe"
    assert track_data["latitude"] == 12.9716
    assert track_data["longitude"] == 77.5946


@pytest.mark.asyncio
async def test_tracking_endpoint_invalid_and_expired_token(client: AsyncClient, db_session: AsyncSession):
    # Fake token
    res_fake = await client.get("/api/v1/track/invalid-fake-token-999")
    assert res_fake.status_code == 404

    # Expired token
    device = Device(device_code=f"SIM-EXP-{uuid.uuid4().hex[:4]}", device_type="simulator")
    db_session.add(device)
    await db_session.commit()

    reading = SensorReading(
        device_id=device.id,
        accel_x=1.0,
        accel_y=1.0,
        accel_z=9.8,
        gas_level=50.0,
        latitude=12.9000,
        longitude=77.5000,
        recorded_at=datetime.now(timezone.utc),
    )
    db_session.add(reading)
    await db_session.commit()

    incident = Incident(
        device_id=device.id,
        sensor_reading_id=reading.id,
        incident_type="accident",
        severity="severe",
        latitude=12.9000,
        longitude=77.5000,
        status="open",
    )
    db_session.add(incident)
    await db_session.commit()

    # Create expired token
    expired_tok = IncidentTrackingToken(
        incident_id=incident.id,
        token=f"expired-tok-{uuid.uuid4().hex[:8]}",
        created_at=datetime.now(timezone.utc) - timedelta(hours=30),
        expires_at=datetime.now(timezone.utc) - timedelta(hours=6),
    )
    db_session.add(expired_tok)
    await db_session.commit()

    res_exp = await client.get(f"/api/v1/track/{expired_tok.token}")
    assert res_exp.status_code == 404
