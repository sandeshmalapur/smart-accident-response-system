import uuid
from datetime import datetime, timezone
import pytest
from app.db.models import SensorReading, Incident
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def test_filter_incidents_by_sensor_reading_id(client, test_user, test_device, db_session: AsyncSession):
    # 1. Login to get token
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "testpassword123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create sensor readings
    sr1 = SensorReading(
        device_id=test_device.id,
        accel_x=2.5,
        accel_y=0.1,
        accel_z=9.8,
        gas_level=120.0,
        latitude=12.97,
        longitude=77.59,
        recorded_at=datetime.now(timezone.utc),
    )
    sr2 = SensorReading(
        device_id=test_device.id,
        accel_x=0.0,
        accel_y=0.0,
        accel_z=9.8,
        gas_level=500.0,
        latitude=12.97,
        longitude=77.59,
        recorded_at=datetime.now(timezone.utc),
    )
    db_session.add_all([sr1, sr2])
    await db_session.commit()
    await db_session.refresh(sr1)
    await db_session.refresh(sr2)

    # 3. Create incidents (2 for sr1, 1 for sr2)
    inc1 = Incident(
        device_id=test_device.id,
        sensor_reading_id=sr1.id,
        incident_type="accident",
        severity="severe",
        severity_score=0.9,
        latitude=12.97,
        longitude=77.59,
    )
    inc2 = Incident(
        device_id=test_device.id,
        sensor_reading_id=sr1.id,
        incident_type="gas_leak",
        anomaly_score=0.8,
        latitude=12.97,
        longitude=77.59,
    )
    inc3 = Incident(
        device_id=test_device.id,
        sensor_reading_id=sr2.id,
        incident_type="gas_leak",
        anomaly_score=0.95,
        latitude=12.97,
        longitude=77.59,
    )
    db_session.add_all([inc1, inc2, inc3])
    await db_session.commit()

    # 4. Query incidents filtering by sr1.id
    resp = await client.get(f"/api/v1/incidents?sensor_reading_id={sr1.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert len(data) == 2
    for item in data:
        assert item["sensor_reading_id"] == str(sr1.id)
    
    types = {item["incident_type"] for item in data}
    assert types == {"accident", "gas_leak"}
