import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DeviceCreate(BaseModel):
    device_code: str
    device_type: Literal["simulator", "esp32"]
    label: str | None = None


class DeviceOut(BaseModel):
    id: uuid.UUID
    device_code: str
    device_type: str
    label: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
