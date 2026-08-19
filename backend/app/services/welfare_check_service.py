import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Device, WelfareCheck


async def create_welfare_check(db: AsyncSession, incident_id: uuid.UUID, device_id: uuid.UUID) -> WelfareCheck:
    now = datetime.now(timezone.utc)
    welfare_check = WelfareCheck(
        incident_id=incident_id,
        device_id=device_id,
        status="awaiting_response",
        initiated_at=now,
    )
    db.add(welfare_check)
    await db.commit()
    await db.refresh(welfare_check)
    return welfare_check


async def respond_to_welfare_check(db: AsyncSession, check: WelfareCheck, response: str) -> WelfareCheck:
    if response not in ("ok", "help"):
        raise ValueError(f"Invalid response '{response}'. Must be 'ok' or 'help'")

    if check.status != "awaiting_response":
        raise ValueError(f"Welfare check is currently '{check.status}', cannot submit response")

    now = datetime.now(timezone.utc)
    check.response = response
    check.responded_at = now
    if response == "ok":
        check.status = "responded_ok"
    elif response == "help":
        check.status = "responded_help"

    await db.commit()
    await db.refresh(check)
    return check


async def get_welfare_check_by_id(db: AsyncSession, check_id: uuid.UUID) -> WelfareCheck | None:
    res = await db.execute(select(WelfareCheck).where(WelfareCheck.id == check_id))
    return res.scalar_one_or_none()


async def get_latest_active_check_by_device_code(db: AsyncSession, device_code: str) -> WelfareCheck | None:
    stmt = (
        select(WelfareCheck)
        .join(Device, WelfareCheck.device_id == Device.id)
        .where(Device.device_code == device_code)
        .order_by(WelfareCheck.initiated_at.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().first()


async def list_welfare_checks(
    db: AsyncSession,
    incident_id: uuid.UUID | None = None,
    device_id: uuid.UUID | None = None,
    status: str | None = None,
) -> list[WelfareCheck]:
    stmt = select(WelfareCheck).order_by(WelfareCheck.initiated_at.desc())
    if incident_id is not None:
        stmt = stmt.where(WelfareCheck.incident_id == incident_id)
    if device_id is not None:
        stmt = stmt.where(WelfareCheck.device_id == device_id)
    if status is not None:
        stmt = stmt.where(WelfareCheck.status == status)

    res = await db.execute(stmt)
    return list(res.scalars().all())


async def escalate_expired_welfare_checks(
    db: AsyncSession, timeout_seconds: float = 90.0
) -> list[WelfareCheck]:
    now = datetime.now(timezone.utc)
    stmt = select(WelfareCheck).where(WelfareCheck.status == "awaiting_response")
    res = await db.execute(stmt)
    awaiting_checks = list(res.scalars().all())

    escalated = []
    for check in awaiting_checks:
        elapsed = (now - check.initiated_at).total_seconds()
        if elapsed >= timeout_seconds:
            check.status = "no_response_escalated"
            check.escalated_at = now
            escalated.append(check)

    if escalated:
        await db.commit()
        for check in escalated:
            await db.refresh(check)

    return escalated
