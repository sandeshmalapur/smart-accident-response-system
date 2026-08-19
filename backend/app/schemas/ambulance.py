import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AmbulanceCreate(BaseModel):
    ambulance_code: str = Field(..., min_length=1, max_length=100)
    label: str | None = Field(default=None, max_length=255)


class AmbulanceOut(BaseModel):
    id: uuid.UUID
    ambulance_code: str
    label: str | None = None
    current_latitude: float | None = None
    current_longitude: float | None = None
    status: str
    last_location_update: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AmbulanceNearestOut(AmbulanceOut):
    distance_km: float


class MqttAmbulanceLocationPayload(BaseModel):
    ambulance_code: str
    latitude: float
    longitude: float
    timestamp: str | datetime | None = None
