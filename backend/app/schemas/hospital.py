import uuid
from datetime import datetime

from pydantic import BaseModel


class HospitalCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    phone: str | None = None


class HospitalOut(BaseModel):
    id: uuid.UUID
    name: str
    latitude: float
    longitude: float
    phone: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class HospitalNearestOut(HospitalOut):
    distance_km: float
