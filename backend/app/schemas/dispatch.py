import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ambulance import AmbulanceOut
from app.schemas.incident import IncidentOut


class DispatchCreate(BaseModel):
    ambulance_id: uuid.UUID


class DispatchUpdate(BaseModel):
    status: str = Field(..., description="Status values: en_route, arrived, completed, cancelled")


class DispatchOut(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    ambulance_id: uuid.UUID
    dispatched_by: uuid.UUID
    status: str
    dispatched_at: datetime
    updated_at: datetime
    ambulance: AmbulanceOut | None = None
    incident: IncidentOut | None = None

    model_config = ConfigDict(from_attributes=True)
