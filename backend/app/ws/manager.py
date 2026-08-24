"""
WebSocket connection manager for /ws/live.

Tracks active connections and broadcasts reading/incident/alert events
to all of them, per the message shapes in API_SPEC.md.
"""
import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("app.ws")


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        logger.info("WebSocket connected (active=%d)", len(self._connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)
        logger.info("WebSocket disconnected (active=%d)", len(self._connections))

    async def broadcast(self, message_type: str, data: dict[str, Any]) -> None:
        """Broadcast a {type, data} envelope to all connected clients."""
        payload = {"type": message_type, "data": data}
        dead: list[WebSocket] = []
        async with self._lock:
            connections = list(self._connections)
        for ws in connections:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.discard(ws)

    async def broadcast_reading(self, reading: dict[str, Any]) -> None:
        await self.broadcast("reading", reading)

    async def broadcast_incident(self, incident: dict[str, Any]) -> None:
        await self.broadcast("incident", incident)

    async def broadcast_alert(self, alert: dict[str, Any]) -> None:
        await self.broadcast("alert", alert)

    async def broadcast_welfare_check(self, welfare_check: dict[str, Any]) -> None:
        await self.broadcast("welfare_check", welfare_check)

    async def broadcast_agency_dispatch(self, agency_dispatch: dict[str, Any]) -> None:
        await self.broadcast("agency_dispatch", agency_dispatch)

    async def broadcast_incident_response_status(self, response_status_data: dict[str, Any]) -> None:
        await self.broadcast("incident_response_status", response_status_data)


# Single process-wide instance shared by the MQTT client, REST routers, and the WS route.
manager = ConnectionManager()


