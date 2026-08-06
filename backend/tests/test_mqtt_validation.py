import pytest
from pydantic import ValidationError

from app.schemas.reading import MqttStatusPayload, MqttTelemetryPayload

VALID_TELEMETRY = {
    "device_code": "SIM-001",
    "recorded_at": "2026-08-06T10:15:30.123Z",
    "accel": {"x": 0.12, "y": -0.05, "z": 9.81},
    "gyro": {"x": 0.01, "y": 0.02, "z": -0.01},
    "gas_level": 120.5,
    "gps": {"lat": 12.9141, "lng": 74.8560},
}


def test_valid_telemetry_payload_accepted():
    payload = MqttTelemetryPayload.model_validate(VALID_TELEMETRY)
    assert payload.device_code == "SIM-001"
    assert payload.accel.z == 9.81
    assert payload.gps.lat == 12.9141


def test_telemetry_payload_gyro_is_optional():
    data = {k: v for k, v in VALID_TELEMETRY.items() if k != "gyro"}
    payload = MqttTelemetryPayload.model_validate(data)
    assert payload.gyro is None


@pytest.mark.parametrize(
    "missing_field",
    ["device_code", "recorded_at", "accel", "gas_level", "gps"],
)
def test_telemetry_payload_missing_required_field_rejected(missing_field):
    data = dict(VALID_TELEMETRY)
    del data[missing_field]
    with pytest.raises(ValidationError):
        MqttTelemetryPayload.model_validate(data)


def test_telemetry_payload_malformed_types_rejected():
    data = dict(VALID_TELEMETRY)
    data["accel"] = "not-an-object"
    with pytest.raises(ValidationError):
        MqttTelemetryPayload.model_validate(data)


def test_valid_status_payload_accepted():
    payload = MqttStatusPayload.model_validate(
        {"device_code": "SIM-001", "status": "online", "timestamp": "2026-08-06T10:15:00.000Z"}
    )
    assert payload.status == "online"


def test_status_payload_missing_field_rejected():
    with pytest.raises(ValidationError):
        MqttStatusPayload.model_validate({"device_code": "SIM-001", "status": "online"})
