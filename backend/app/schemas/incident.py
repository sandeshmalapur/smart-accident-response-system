import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.alert import AlertOut
from app.schemas.hospital import HospitalOut
from app.schemas.reading import SensorReadingOut


class IncidentOut(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    sensor_reading_id: uuid.UUID
    nearest_hospital_id: uuid.UUID | None = None
    incident_type: str
    severity: str | None
    severity_score: float | None
    anomaly_score: float | None
    latitude: float
    longitude: float
    status: str
    created_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class IncidentDetailOut(IncidentOut):
    sensor_reading: SensorReadingOut
    nearest_hospital: HospitalOut | None = None
    alerts: list[AlertOut] = []


class IncidentUpdate(BaseModel):
    status: Literal["acknowledged", "resolved", "false_positive"]
