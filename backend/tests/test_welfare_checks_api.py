import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import welfare_messages
from app.db.models import Device, Incident, SensorReading, WelfareCheck
from app.ml.inference import InferenceResult
from app.services import incident_service, welfare_check_service


@pytest.fixture
async def sample_device(db_session: AsyncSession) -> Device:
    device = Device(device_code=f"DEV-WC-{uuid.uuid4().hex[:6]}", device_type="simulator")
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return device


@pytest.fixture
async def sample_reading(db_session: AsyncSession, sample_device: Device) -> SensorReading:
    reading = SensorReading(
        device_id=sample_device.id,
        accel_x=28.0,
        accel_y=12.0,
        accel_z=4.0,
        gas_level=180.0,
        latitude=12.9716,
        longitude=77.5946,
        recorded_at=datetime.now(timezone.utc),
    )
    db_session.add(reading)
    await db_session.commit()
    await db_session.refresh(reading)
    return reading


@pytest.mark.asyncio
async def test_get_static_welfare_messages(client: AsyncClient):
    res = await client.get("/api/v1/welfare-checks/config/messages")
    assert res.status_code == 200
    data = res.json()
    assert data["prompt"] == welfare_messages.WELFARE_CHECK_PROMPT
    assert data["safety_guidance"] == welfare_messages.SAFETY_GUIDANCE
    assert data["escalation_notice"] == welfare_messages.ESCALATION_NOTICE


@pytest.mark.asyncio
async def test_auto_create_welfare_check_on_severe_accident(
    db_session: AsyncSession, sample_device: Device, sample_reading: SensorReading
):
    result = InferenceResult(
        is_incident=True,
        incident_type="accident",
        severity="severe",
        severity_score=0.98,
        anomaly_score=None,
    )
    incident = await incident_service.create_incident_from_inference(
        db_session,
        device_id=sample_device.id,
        sensor_reading_id=sample_reading.id,
        latitude=sample_reading.latitude,
        longitude=sample_reading.longitude,
        result=result,
    )
    assert incident.severity == "severe"

    checks = await welfare_check_service.list_welfare_checks(db_session, incident_id=incident.id)
    assert len(checks) == 1
    assert checks[0].status == "awaiting_response"
    assert checks[0].device_id == sample_device.id


@pytest.mark.asyncio
async def test_no_welfare_check_on_moderate_or_gas_leak(
    db_session: AsyncSession, sample_device: Device, sample_reading: SensorReading
):
    # Moderate accident
    mod_result = InferenceResult(
        is_incident=True,
        incident_type="accident",
        severity="moderate",
        severity_score=0.60,
        anomaly_score=None,
    )
    inc_mod = await incident_service.create_incident_from_inference(
        db_session,
        device_id=sample_device.id,
        sensor_reading_id=sample_reading.id,
        latitude=sample_reading.latitude,
        longitude=sample_reading.longitude,
        result=mod_result,
    )
    checks_mod = await welfare_check_service.list_welfare_checks(db_session, incident_id=inc_mod.id)
    assert len(checks_mod) == 0

    # Gas leak
    gas_result = InferenceResult(
        is_incident=True,
        incident_type="gas_leak",
        severity=None,
        severity_score=None,
        anomaly_score=0.95,
    )
    inc_gas = await incident_service.create_incident_from_inference(
        db_session,
        device_id=sample_device.id,
        sensor_reading_id=sample_reading.id,
        latitude=sample_reading.latitude,
        longitude=sample_reading.longitude,
        result=gas_result,
    )
    checks_gas = await welfare_check_service.list_welfare_checks(db_session, incident_id=inc_gas.id)
    assert len(checks_gas) == 0


@pytest.mark.asyncio
async def test_respond_welfare_check_ok_and_help(
    client: AsyncClient, db_session: AsyncSession, sample_device: Device, sample_reading: SensorReading
):
    # Create incident + welfare check
    result = InferenceResult(
        is_incident=True,
        incident_type="accident",
        severity="severe",
        severity_score=0.99,
        anomaly_score=None,
    )
    incident = await incident_service.create_incident_from_inference(
        db_session,
        device_id=sample_device.id,
        sensor_reading_id=sample_reading.id,
        latitude=sample_reading.latitude,
        longitude=sample_reading.longitude,
        result=result,
    )
    checks = await welfare_check_service.list_welfare_checks(db_session, incident_id=incident.id)
    check_id = checks[0].id

    # Unauthenticated respond "ok"
    res_ok = await client.post(f"/api/v1/welfare-checks/{check_id}/respond", json={"response": "ok"})
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "responded_ok"
    assert res_ok.json()["response"] == "ok"
    assert res_ok.json()["safety_guidance"] == welfare_messages.SAFETY_GUIDANCE

    # Double response attempt rejected
    res_double = await client.post(f"/api/v1/welfare-checks/{check_id}/respond", json={"response": "help"})
    assert res_double.status_code == 400


@pytest.mark.asyncio
async def test_escalate_expired_welfare_checks(
    db_session: AsyncSession, sample_device: Device, sample_reading: SensorReading
):
    # Create severe accident incident
    result = InferenceResult(
        is_incident=True,
        incident_type="accident",
        severity="severe",
        severity_score=0.97,
        anomaly_score=None,
    )
    incident = await incident_service.create_incident_from_inference(
        db_session,
        device_id=sample_device.id,
        sensor_reading_id=sample_reading.id,
        latitude=sample_reading.latitude,
        longitude=sample_reading.longitude,
        result=result,
    )
    checks = await welfare_check_service.list_welfare_checks(db_session, incident_id=incident.id)
    check = checks[0]

    # Backdate initiated_at to 100 seconds ago
    check.initiated_at = datetime.now(timezone.utc) - timedelta(seconds=100)
    await db_session.commit()

    escalated = await welfare_check_service.escalate_expired_welfare_checks(db_session, timeout_seconds=90.0)
    assert len(escalated) >= 1
    escalated_ids = [c.id for c in escalated]
    assert check.id in escalated_ids

    # Confirm status in DB
    refreshed = await welfare_check_service.get_welfare_check_by_id(db_session, check.id)
    assert refreshed is not None
    assert refreshed.status == "no_response_escalated"
    assert refreshed.escalated_at is not None
