import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AlertOut(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    channel: str
    recipient: str | None
    payload: dict[str, Any]
    dispatched_at: datetime
    delivery_status: str

    model_config = {"from_attributes": True}
