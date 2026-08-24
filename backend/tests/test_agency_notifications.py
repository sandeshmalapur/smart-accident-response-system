import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.db.models import AgencyUnit, Alert, Device, Incident, SensorReading, User


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
async def test_agency_dispatch_creates_mock_alert(
    client: AsyncClient, operator_user: User, sample_incident: Incident, db_session: AsyncSession
):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    unit_code = f"POL-{uuid.uuid4().hex[:4]}"
    unit = AgencyUnit(agency_type="police", unit_code=unit_code, status="available", contact_phone=None)
    db_session.add(unit)
    await db_session.commit()
    await db_session.refresh(unit)

    res = await client.post(
        f"/api/v1/incidents/{sample_incident.id}/dispatch-agency",
        json={"agency_type": "police", "agency_unit_id": str(unit.id)},
        headers=headers,
    )
    assert res.status_code == 201

    # Check alert table row
    alerts_res = await db_session.execute(
        select(Alert).where(Alert.incident_id == sample_incident.id)
    )
    alerts = list(alerts_res.scalars().all())
    assert len(alerts) >= 1
    alert = next(a for a in alerts if a.payload.get("unit_code") == unit_code)
    assert alert.channel == "mock"
    assert alert.delivery_status == "mocked"
    assert alert.payload["unit_code"] == unit_code
    assert alert.payload["severity"] == "severe"


@pytest.mark.asyncio
async def test_agency_dispatch_resilient_to_sms_failure(
    client: AsyncClient, operator_user: User, sample_incident: Incident, db_session: AsyncSession
):
    token = create_access_token(str(operator_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    unit = AgencyUnit(agency_type="fire", unit_code=f"FIRE-{uuid.uuid4().hex[:4]}", status="available")
    db_session.add(unit)
    await db_session.commit()
    await db_session.refresh(unit)

    with patch("app.services.sms_service.notify_agency_unit", side_effect=RuntimeError("SMS Gateway down")):
        res = await client.post(
            f"/api/v1/incidents/{sample_incident.id}/dispatch-agency",
            json={"agency_type": "fire", "agency_unit_id": str(unit.id)},
            headers=headers,
        )
        assert res.status_code == 201
        assert res.json()["status"] == "pending"
