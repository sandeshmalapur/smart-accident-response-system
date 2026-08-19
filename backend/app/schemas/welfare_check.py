import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WelfareCheckRespond(BaseModel):
    response: str = Field(..., description="Values: 'ok' or 'help'")


class WelfareCheckOut(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    device_id: uuid.UUID
    status: str
    initiated_at: datetime
    responded_at: datetime | None = None
    response: str | None = None
    escalated_at: datetime | None = None
    prompt: str | None = None
    safety_guidance: str | None = None
    escalation_notice: str | None = None

    model_config = ConfigDict(from_attributes=True)


class WelfareCheckMessagesOut(BaseModel):
    prompt: str
    safety_guidance: str
    escalation_notice: str
