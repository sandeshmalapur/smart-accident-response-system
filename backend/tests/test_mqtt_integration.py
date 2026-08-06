"""
Integration test: simulates the MQTT subscriber's handling of a telemetry
message directly (bypassing the network broker) and asserts a
sensor_readings row is created — the same code path used when a real
message arrives via Mosquitto.
"""
import pytest
from sqlalchemy import select

from app.db.models import SensorReading
from app.mqtt.client import MqttSubscriber

pytestmark = pytest.mark.asyncio


async def test_valid_telemetry_creates_sensor_reading(db_session, test_device):
    subscriber = MqttSubscriber()
    payload = {
        "device_code": test_device.device_code,
        "recorded_at": "2026-08-06T10:15:30.123Z",
        "accel": {"x": 0.12, "y": -0.05, "z": 9.81},
        "gyro": {"x": 0.01, "y": 0.02, "z": -0.01},
        "gas_level": 120.5,
        "gps": {"lat": 12.9141, "lng": 74.8560},
    }

    await subscriber._handle_telemetry(payload)

    result = await db_session.execute(
        select(SensorReading).where(SensorReading.device_id == test_device.id)
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].gas_level == 120.5
    assert rows[0].latitude == 12.9141


async def test_telemetry_for_unknown_device_is_dropped(db_session):
    subscriber = MqttSubscriber()
    payload = {
        "device_code": "DOES-NOT-EXIST",
        "recorded_at": "2026-08-06T10:15:30.123Z",
        "accel": {"x": 0.1, "y": 0.1, "z": 9.8},
        "gas_level": 100.0,
        "gps": {"lat": 0.0, "lng": 0.0},
    }
    # Should not raise, and should not persist anything.
    await subscriber._handle_telemetry(payload)

    result = await db_session.execute(
        select(SensorReading).where(SensorReading.device_id.is_(None))
    )
    assert result.scalars().all() == []


async def test_malformed_telemetry_does_not_crash():
    subscriber = MqttSubscriber()
    # Missing required fields entirely.
    await subscriber._handle_telemetry({"device_code": "SIM-001"})
    # Reaching this line means no exception propagated.
    assert True
