import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.security import TokenPayloadError, decode_access_token
from app.db.session import AsyncSessionLocal
from app.services.auth_service import get_user_by_id
from app.ws.manager import manager

router = APIRouter(tags=["ws"])


@router.websocket("/ws/live")
async def ws_live(websocket: WebSocket, token: str | None = None) -> None:
    """
    Broadcast-only channel per API_SPEC.md: auth via ?token=... query param,
    server pushes {type: reading|incident|alert, data: {...}} messages.
    No client -> server messages are expected in Phase 1.
    """
    if token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (TokenPayloadError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    async with AsyncSessionLocal() as db:
        user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket)
    try:
        while True:
            # Broadcast-only channel; drain/ignore any client messages.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)
