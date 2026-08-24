import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AgencyUnitCreate(BaseModel):
    agency_type: str = Field(..., description="Agency type: police or fire")
    unit_code: str = Field(..., min_length=1, max_length=100)
    label: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=50)
    current_latitude: float | None = None
    current_longitude: float | None = None


class AgencyUnitOut(BaseModel):
    id: uuid.UUID
    agency_type: str
    unit_code: str
    label: str | None = None
    contact_phone: str | None = None
    current_latitude: float | None = None
    current_longitude: float | None = None
    status: str
    last_location_update: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgencyUnitNearestOut(AgencyUnitOut):
    distance_km: float
