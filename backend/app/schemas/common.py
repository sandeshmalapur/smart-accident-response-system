from typing import Any, Literal

from pydantic import BaseModel


class WsMessage(BaseModel):
    """Server -> client message shape for /ws/live, per API_SPEC.md."""

    type: Literal["reading", "incident", "alert"]
    data: dict[str, Any]
