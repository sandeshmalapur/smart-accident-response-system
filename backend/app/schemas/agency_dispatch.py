import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.agency_unit import AgencyUnitOut
from app.schemas.incident import IncidentOut


class AgencyDispatchCreate(BaseModel):
    agency_type: str = Field(..., description="Agency type: police or fire")
    agency_unit_id: uuid.UUID


class AgencyDispatchUpdate(BaseModel):
    status: str = Field(..., description="Status values: en_route, on_scene, completed, cancelled")


class AgencyDispatchOut(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    agency_unit_id: uuid.UUID
    dispatched_by: uuid.UUID | None = None
    agency_type: str
    status: str
    dispatched_at: datetime
    updated_at: datetime
    agency_unit: AgencyUnitOut | None = None
    incident: IncidentOut | None = None

    model_config = ConfigDict(from_attributes=True)
