import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.db.models import AgencyDispatch, AgencyUnit, Ambulance, Device, Dispatch, Incident, SensorReading, User


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
async def test_response_status_no_response(client: AsyncClient, operator_user: User, sample_incident: Incident):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get(f"/api/v1/incidents/{sample_incident.id}/response-status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["incident_id"] == str(sample_incident.id)
    assert data["ambulance"] is None
    assert data["police"] is None
    assert data["fire"] is None
    assert data["overall_status"] == "no_response"


@pytest.mark.asyncio
async def test_response_status_responding(
    client: AsyncClient, operator_user: User, sample_incident: Incident, db_session: AsyncSession
):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    amb = Ambulance(ambulance_code=f"AMB-{uuid.uuid4().hex[:4]}", status="dispatched")
    db_session.add(amb)
    await db_session.commit()

    disp = Dispatch(
        incident_id=sample_incident.id,
        ambulance_id=amb.id,
        dispatched_by=operator_user.id,
        status="en_route",
    )
    db_session.add(disp)
    await db_session.commit()

    res = await client.get(f"/api/v1/incidents/{sample_incident.id}/response-status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["ambulance"]["status"] == "en_route"
    assert data["ambulance"]["ambulance_code"] == amb.ambulance_code
    assert data["overall_status"] == "responding"


@pytest.mark.asyncio
async def test_response_status_resolved(
    client: AsyncClient, operator_user: User, sample_incident: Incident, db_session: AsyncSession
):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    amb = Ambulance(ambulance_code=f"AMB-{uuid.uuid4().hex[:4]}", status="available")
    pol = AgencyUnit(agency_type="police", unit_code=f"POL-{uuid.uuid4().hex[:4]}", status="available")
    db_session.add_all([amb, pol])
    await db_session.commit()

    d1 = Dispatch(
        incident_id=sample_incident.id,
        ambulance_id=amb.id,
        dispatched_by=operator_user.id,
        status="completed",
    )
    d2 = AgencyDispatch(
        incident_id=sample_incident.id,
        agency_unit_id=pol.id,
        dispatched_by=operator_user.id,
        agency_type="police",
        status="completed",
    )
    db_session.add_all([d1, d2])
    await db_session.commit()

    res = await client.get(f"/api/v1/incidents/{sample_incident.id}/response-status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["overall_status"] == "resolved"


@pytest.mark.asyncio
async def test_response_status_one_cancelled_one_completed(
    client: AsyncClient, operator_user: User, sample_incident: Incident, db_session: AsyncSession
):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    amb = Ambulance(ambulance_code=f"AMB-{uuid.uuid4().hex[:4]}", status="available")
    fire = AgencyUnit(agency_type="fire", unit_code=f"FIRE-{uuid.uuid4().hex[:4]}", status="available")
    db_session.add_all([amb, fire])
    await db_session.commit()

    d1 = Dispatch(
        incident_id=sample_incident.id,
        ambulance_id=amb.id,
        dispatched_by=operator_user.id,
        status="cancelled",
    )
    d2 = AgencyDispatch(
        incident_id=sample_incident.id,
        agency_unit_id=fire.id,
        dispatched_by=operator_user.id,
        agency_type="fire",
        status="completed",
    )
    db_session.add_all([d1, d2])
    await db_session.commit()

    res = await client.get(f"/api/v1/incidents/{sample_incident.id}/response-status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["overall_status"] == "resolved"


@pytest.mark.asyncio
async def test_response_status_all_cancelled(
    client: AsyncClient, operator_user: User, sample_incident: Incident, db_session: AsyncSession
):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    amb = Ambulance(ambulance_code=f"AMB-{uuid.uuid4().hex[:4]}", status="available")
    db_session.add(amb)
    await db_session.commit()

    d1 = Dispatch(
        incident_id=sample_incident.id,
        ambulance_id=amb.id,
        dispatched_by=operator_user.id,
        status="cancelled",
    )
    db_session.add(d1)
    await db_session.commit()

    res = await client.get(f"/api/v1/incidents/{sample_incident.id}/response-status", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["overall_status"] == "no_response"


@pytest.mark.asyncio
async def test_response_status_404(client: AsyncClient, operator_user: User):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get(f"/api/v1/incidents/{uuid.uuid4()}/response-status", headers=headers)
    assert res.status_code == 404
