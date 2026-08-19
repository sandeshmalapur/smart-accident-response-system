import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core import welfare_messages
from app.db.session import get_db
from app.schemas.welfare_check import (
    WelfareCheckMessagesOut,
    WelfareCheckOut,
    WelfareCheckRespond,
)
from app.services import welfare_check_service
from app.ws.manager import manager

router = APIRouter(prefix="/welfare-checks", tags=["welfare-checks"])


def _attach_messages(out_dict: dict) -> dict:
    out_dict["prompt"] = welfare_messages.WELFARE_CHECK_PROMPT
    out_dict["safety_guidance"] = welfare_messages.SAFETY_GUIDANCE
    out_dict["escalation_notice"] = welfare_messages.ESCALATION_NOTICE
    return out_dict


@router.get("/config/messages", response_model=WelfareCheckMessagesOut)
async def get_welfare_messages() -> WelfareCheckMessagesOut:
    return WelfareCheckMessagesOut(
        prompt=welfare_messages.WELFARE_CHECK_PROMPT,
        safety_guidance=welfare_messages.SAFETY_GUIDANCE,
        escalation_notice=welfare_messages.ESCALATION_NOTICE,
    )


@router.post("/{check_id}/respond", response_model=WelfareCheckOut)
async def respond_to_welfare_check(
    check_id: uuid.UUID,
    payload: WelfareCheckRespond,
    db: AsyncSession = Depends(get_db),
) -> WelfareCheckOut:
    check = await welfare_check_service.get_welfare_check_by_id(db, check_id)
    if check is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Welfare check not found")

    try:
        updated = await welfare_check_service.respond_to_welfare_check(db, check, payload.response)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    out_data = _attach_messages(WelfareCheckOut.model_validate(updated).model_dump(mode="json"))
    await manager.broadcast_welfare_check(out_data)
    return WelfareCheckOut(**out_data)


@router.get("/device/{device_code}", response_model=WelfareCheckOut)
async def get_welfare_check_by_device(
    device_code: str, db: AsyncSession = Depends(get_db)
) -> WelfareCheckOut:
    check = await welfare_check_service.get_latest_active_check_by_device_code(db, device_code)
    if check is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active welfare check for device")
    out_data = _attach_messages(WelfareCheckOut.model_validate(check).model_dump(mode="json"))
    return WelfareCheckOut(**out_data)


@router.get("/{check_id}", response_model=WelfareCheckOut)
async def get_welfare_check(
    check_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> WelfareCheckOut:
    check = await welfare_check_service.get_welfare_check_by_id(db, check_id)
    if check is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Welfare check not found")
    out_data = _attach_messages(WelfareCheckOut.model_validate(check).model_dump(mode="json"))
    return WelfareCheckOut(**out_data)


@router.get("", response_model=list[WelfareCheckOut], dependencies=[Depends(get_current_user)])
async def list_welfare_checks(
    incident_id: uuid.UUID | None = Query(default=None),
    device_id: uuid.UUID | None = Query(default=None),
    status_: str | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> list[WelfareCheckOut]:
    checks = await welfare_check_service.list_welfare_checks(
        db, incident_id=incident_id, device_id=device_id, status=status_
    )
    result = []
    for c in checks:
        d = _attach_messages(WelfareCheckOut.model_validate(c).model_dump(mode="json"))
        result.append(WelfareCheckOut(**d))
    return result
