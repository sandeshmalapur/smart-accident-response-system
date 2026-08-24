import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.db.models import AgencyDispatch, AgencyUnit, Device, Incident, SensorReading, User


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
async def test_create_agency_dispatch_success(
    client: AsyncClient, operator_user: User, sample_incident: Incident, db_session: AsyncSession
):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    unit = AgencyUnit(agency_type="police", unit_code=f"POL-{uuid.uuid4().hex[:4]}", status="available")
    db_session.add(unit)
    await db_session.commit()
    await db_session.refresh(unit)

    res = await client.post(
        f"/api/v1/incidents/{sample_incident.id}/dispatch-agency",
        json={"agency_type": "police", "agency_unit_id": str(unit.id)},
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["incident_id"] == str(sample_incident.id)
    assert data["agency_unit_id"] == str(unit.id)
    assert data["agency_type"] == "police"
    assert data["status"] == "pending"

    # Verify unit status flipped to 'dispatched'
    await db_session.refresh(unit)
    assert unit.status == "dispatched"


@pytest.mark.asyncio
async def test_create_agency_dispatch_mismatched_agency_type(
    client: AsyncClient, operator_user: User, sample_incident: Incident, db_session: AsyncSession
):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    unit = AgencyUnit(agency_type="police", unit_code=f"POL-{uuid.uuid4().hex[:4]}", status="available")
    db_session.add(unit)
    await db_session.commit()
    await db_session.refresh(unit)

    res = await client.post(
        f"/api/v1/incidents/{sample_incident.id}/dispatch-agency",
        json={"agency_type": "fire", "agency_unit_id": str(unit.id)},
        headers=headers,
    )
    assert res.status_code == 400
    assert "dispatch requested 'fire'" in res.json()["detail"]


@pytest.mark.asyncio
async def test_create_agency_dispatch_unit_unavailable(
    client: AsyncClient, operator_user: User, sample_incident: Incident, db_session: AsyncSession
):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    unit = AgencyUnit(agency_type="fire", unit_code=f"FIRE-{uuid.uuid4().hex[:4]}", status="dispatched")
    db_session.add(unit)
    await db_session.commit()
    await db_session.refresh(unit)

    res = await client.post(
        f"/api/v1/incidents/{sample_incident.id}/dispatch-agency",
        json={"agency_type": "fire", "agency_unit_id": str(unit.id)},
        headers=headers,
    )
    assert res.status_code == 400
    assert "must be 'available' to dispatch" in res.json()["detail"]


@pytest.mark.asyncio
async def test_agency_dispatch_status_transitions_and_cancellation(
    client: AsyncClient, operator_user: User, sample_incident: Incident, db_session: AsyncSession
):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    unit = AgencyUnit(agency_type="police", unit_code=f"POL-{uuid.uuid4().hex[:4]}", status="available")
    db_session.add(unit)
    await db_session.commit()
    await db_session.refresh(unit)

    # 1. Create dispatch
    disp_res = await client.post(
        f"/api/v1/incidents/{sample_incident.id}/dispatch-agency",
        json={"agency_type": "police", "agency_unit_id": str(unit.id)},
        headers=headers,
    )
    dispatch_id = disp_res.json()["id"]

    # 2. Transition to en_route
    r1 = await client.patch(
        f"/api/v1/agency-dispatches/{dispatch_id}",
        json={"status": "en_route"},
        headers=headers,
    )
    assert r1.status_code == 200
    assert r1.json()["status"] == "en_route"
    await db_session.refresh(unit)
    assert unit.status == "dispatched"

    # 3. Transition to on_scene
    r2 = await client.patch(
        f"/api/v1/agency-dispatches/{dispatch_id}",
        json={"status": "on_scene"},
        headers=headers,
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "on_scene"
    await db_session.refresh(unit)
    assert unit.status == "on_scene"

    # 4. Transition to completed -> resets unit to available
    r3 = await client.patch(
        f"/api/v1/agency-dispatches/{dispatch_id}",
        json={"status": "completed"},
        headers=headers,
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == "completed"
    await db_session.refresh(unit)
    assert unit.status == "available"


@pytest.mark.asyncio
async def test_agency_dispatch_cancellation_resets_unit(
    client: AsyncClient, operator_user: User, sample_incident: Incident, db_session: AsyncSession
):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    unit = AgencyUnit(agency_type="fire", unit_code=f"FIRE-{uuid.uuid4().hex[:4]}", status="available")
    db_session.add(unit)
    await db_session.commit()
    await db_session.refresh(unit)

    disp_res = await client.post(
        f"/api/v1/incidents/{sample_incident.id}/dispatch-agency",
        json={"agency_type": "fire", "agency_unit_id": str(unit.id)},
        headers=headers,
    )
    dispatch_id = disp_res.json()["id"]

    # Cancel dispatch
    canc_res = await client.patch(
        f"/api/v1/agency-dispatches/{dispatch_id}",
        json={"status": "cancelled"},
        headers=headers,
    )
    assert canc_res.status_code == 200
    assert canc_res.json()["status"] == "cancelled"

    await db_session.refresh(unit)
    assert unit.status == "available"


@pytest.mark.asyncio
async def test_agency_dispatch_404_cases(client: AsyncClient, operator_user: User):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    # Unknown incident
    res1 = await client.post(
        f"/api/v1/incidents/{uuid.uuid4()}/dispatch-agency",
        json={"agency_type": "police", "agency_unit_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert res1.status_code == 404

    # Unknown dispatch update
    res2 = await client.patch(
        f"/api/v1/agency-dispatches/{uuid.uuid4()}",
        json={"status": "en_route"},
        headers=headers,
    )
    assert res2.status_code == 404
