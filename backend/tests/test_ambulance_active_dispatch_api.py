import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.db.models import Ambulance, Device, Incident, SensorReading, User


@pytest.fixture
async def operator_user(db_session: AsyncSession) -> User:
    email = f"op-{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        hashed_password=hash_password("oppassword123"),
        full_name="Operator User",
        role="operator",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def sample_incident(db_session: AsyncSession) -> Incident:
    device = Device(device_code=f"DEV-{uuid.uuid4().hex[:6]}", device_type="simulator")
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)

    reading = SensorReading(
        device_id=device.id,
        accel_x=15.0,
        accel_y=2.0,
        accel_z=9.8,
        gas_level=120.0,
        latitude=12.9850,
        longitude=77.6050,
        recorded_at=datetime.now(timezone.utc),
    )
    db_session.add(reading)
    await db_session.commit()
    await db_session.refresh(reading)

    incident = Incident(
        device_id=device.id,
        sensor_reading_id=reading.id,
        incident_type="accident",
        severity="severe",
        latitude=12.9850,
        longitude=77.6050,
        status="open",
    )
    db_session.add(incident)
    await db_session.commit()
    await db_session.refresh(incident)
    return incident


@pytest.mark.asyncio
async def test_get_active_dispatch_returns_null_when_available(client: AsyncClient, db_session: AsyncSession):
    amb_code = f"AMB-IDLE-{uuid.uuid4().hex[:4]}"
    amb = Ambulance(
        ambulance_code=amb_code,
        label="Idle Unit",
        current_latitude=12.9716,
        current_longitude=77.5946,
        status="available",
    )
    db_session.add(amb)
    await db_session.commit()

    # By UUID
    res1 = await client.get(f"/api/v1/ambulances/{amb.id}/active-dispatch")
    assert res1.status_code == 200
    assert res1.json() is None

    # By ambulance_code
    res2 = await client.get(f"/api/v1/ambulances/{amb_code}/active-dispatch")
    assert res2.status_code == 200
    assert res2.json() is None


@pytest.mark.asyncio
async def test_get_active_dispatch_returns_dispatch_with_incident(
    client: AsyncClient, operator_user: User, sample_incident: Incident, db_session: AsyncSession
):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    amb_code = f"AMB-NAV-{uuid.uuid4().hex[:4]}"
    amb = Ambulance(
        ambulance_code=amb_code,
        label="Nav Unit",
        current_latitude=12.9716,
        current_longitude=77.5946,
        status="available",
    )
    db_session.add(amb)
    await db_session.commit()
    await db_session.refresh(amb)

    # 1. Create dispatch
    disp_res = await client.post(
        f"/api/v1/incidents/{sample_incident.id}/dispatch",
        json={"ambulance_id": str(amb.id)},
        headers=headers,
    )
    assert disp_res.status_code == 201

    # 2. Check active dispatch endpoint
    res = await client.get(f"/api/v1/ambulances/{amb_code}/active-dispatch")
    assert res.status_code == 200
    data = res.json()
    assert data is not None
    assert data["status"] == "dispatched"
    assert data["ambulance_id"] == str(amb.id)
    assert data["incident"]["latitude"] == 12.9850
    assert data["incident"]["longitude"] == 77.6050

    # 3. Update dispatch to completed -> active-dispatch should return null
    dispatch_id = data["id"]
    comp_res = await client.patch(
        f"/api/v1/dispatches/{dispatch_id}",
        json={"status": "completed"},
        headers=headers,
    )
    assert comp_res.status_code == 200

    res_after = await client.get(f"/api/v1/ambulances/{amb_code}/active-dispatch")
    assert res_after.status_code == 200
    assert res_after.json() is None
