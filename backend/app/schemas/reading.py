import uuid
from datetime import datetime

from pydantic import BaseModel


class SensorReadingOut(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float | None
    gyro_y: float | None
    gyro_z: float | None
    gas_level: float
    latitude: float
    longitude: float
    recorded_at: datetime
    received_at: datetime

    model_config = {"from_attributes": True}


class MqttAccel(BaseModel):
    x: float
    y: float
    z: float


class MqttGyro(BaseModel):
    x: float | None = None
    y: float | None = None
    z: float | None = None


class MqttGps(BaseModel):
    lat: float
    lng: float


class MqttTelemetryPayload(BaseModel):
    """
    Validates the exact shape defined in MQTT_SPEC.md for
    safe/{device_code}/telemetry. This is the frozen wire contract —
    do not rename fields or restructure without a MQTT_SPEC.md version bump.
    """

    device_code: str
    recorded_at: datetime
    accel: MqttAccel
    gyro: MqttGyro | None = None
    gas_level: float
    gps: MqttGps


class MqttStatusPayload(BaseModel):
    """Validates safe/{device_code}/status payloads."""

    device_code: str
    status: str  # "online" | "offline"
    timestamp: datetime
