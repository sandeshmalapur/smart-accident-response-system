import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.db.models import Ambulance, Device, Incident, SensorReading, User


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

    from datetime import datetime, timezone
    reading = SensorReading(
        device_id=device.id,
        accel_x=2.5,
        accel_y=0.1,
        accel_z=9.8,
        gas_level=200.0,
        latitude=12.9716,
        longitude=77.5946,
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
        latitude=12.9716,
        longitude=77.5946,
        status="open",
    )
    db_session.add(incident)
    await db_session.commit()
    await db_session.refresh(incident)
    return incident


@pytest.mark.asyncio
async def test_create_ambulance_admin(client: AsyncClient, admin_user: User):
    token = create_access_token(str(admin_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    amb_code = f"AMB-TEST-{uuid.uuid4().hex[:4]}"
    res = await client.post(
        "/api/v1/ambulances",
        json={"ambulance_code": amb_code, "label": "Test Unit 1"},
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["ambulance_code"] == amb_code
    assert data["label"] == "Test Unit 1"
    assert data["status"] == "available"


@pytest.mark.asyncio
async def test_create_ambulance_operator_forbidden(client: AsyncClient, operator_user: User):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.post(
        "/api/v1/ambulances",
        json={"ambulance_code": "AMB-UNAUTH", "label": "Unauthorized Unit"},
        headers=headers,
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_nearest_ambulances(client: AsyncClient, operator_user: User, db_session: AsyncSession):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    # Create 2 ambulances with known locations near Bangalore (12.9716, 77.5946)
    amb1 = Ambulance(
        ambulance_code=f"AMB-NEAR-{uuid.uuid4().hex[:4]}",
        label="Close Unit",
        current_latitude=12.9720,
        current_longitude=77.5950,
        status="available",
    )
    amb2 = Ambulance(
        ambulance_code=f"AMB-FAR-{uuid.uuid4().hex[:4]}",
        label="Far Unit",
        current_latitude=13.0000,
        current_longitude=77.6500,
        status="available",
    )
    db_session.add_all([amb1, amb2])
    await db_session.commit()

    res = await client.get("/api/v1/ambulances/nearest?lat=12.9716&lng=77.5946&limit=100", headers=headers)
    assert res.status_code == 200
    data = res.json()
    codes = [item["ambulance_code"] for item in data]
    assert amb1.ambulance_code in codes
    assert amb2.ambulance_code in codes
    assert codes.index(amb1.ambulance_code) < codes.index(amb2.ambulance_code)


@pytest.mark.asyncio
async def test_dispatch_lifecycle(
    client: AsyncClient, operator_user: User, sample_incident: Incident, db_session: AsyncSession
):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create available ambulance
    amb = Ambulance(
        ambulance_code=f"AMB-DISP-{uuid.uuid4().hex[:4]}",
        label="Dispatch Test Unit",
        current_latitude=12.9716,
        current_longitude=77.5946,
        status="available",
    )
    db_session.add(amb)
    await db_session.commit()
    await db_session.refresh(amb)

    # 2. Dispatch ambulance
    res = await client.post(
        f"/api/v1/incidents/{sample_incident.id}/dispatch",
        json={"ambulance_id": str(amb.id)},
        headers=headers,
    )
    assert res.status_code == 201
    dispatch_data = res.json()
    assert dispatch_data["status"] == "dispatched"
    assert dispatch_data["ambulance_id"] == str(amb.id)
    dispatch_id = dispatch_data["id"]

    # Verify ambulance status updated to dispatched
    amb_res = await client.get(f"/api/v1/ambulances/{amb.id}", headers=headers)
    assert amb_res.json()["status"] == "dispatched"

    # 3. Trying to dispatch same non-available ambulance again fails
    res_fail = await client.post(
        f"/api/v1/incidents/{sample_incident.id}/dispatch",
        json={"ambulance_id": str(amb.id)},
        headers=headers,
    )
    assert res_fail.status_code == 400

    # 4. Update dispatch status: en_route -> arrived -> completed
    res_enroute = await client.patch(
        f"/api/v1/dispatches/{dispatch_id}",
        json={"status": "en_route"},
        headers=headers,
    )
    assert res_enroute.status_code == 200
    assert res_enroute.json()["status"] == "en_route"

    res_arrived = await client.patch(
        f"/api/v1/dispatches/{dispatch_id}",
        json={"status": "arrived"},
        headers=headers,
    )
    assert res_arrived.status_code == 200
    assert res_arrived.json()["status"] == "arrived"

    res_completed = await client.patch(
        f"/api/v1/dispatches/{dispatch_id}",
        json={"status": "completed"},
        headers=headers,
    )
    assert res_completed.status_code == 200
    assert res_completed.json()["status"] == "completed"

    # 5. Confirm ambulance status returned to available
    amb_res_final = await client.get(f"/api/v1/ambulances/{amb.id}", headers=headers)
    assert amb_res_final.json()["status"] == "available"
