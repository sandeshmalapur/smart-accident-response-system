import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Ambulance, Dispatch, Incident


async def create_dispatch(
    db: AsyncSession, incident_id: uuid.UUID, ambulance_id: uuid.UUID, user_id: uuid.UUID
) -> Dispatch:
    # 1. Fetch incident
    inc_res = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = inc_res.scalar_one_or_none()
    if incident is None:
        raise ValueError("Incident not found")

    # 2. Fetch ambulance & verify available status
    amb_res = await db.execute(select(Ambulance).where(Ambulance.id == ambulance_id))
    ambulance = amb_res.scalar_one_or_none()
    if ambulance is None:
        raise ValueError("Ambulance not found")
    if ambulance.status != "available":
        raise ValueError(f"Ambulance is currently '{ambulance.status}', must be 'available' to dispatch")

    # 3. Update ambulance status
    ambulance.status = "dispatched"

    # 4. Create dispatch row
    now = datetime.now(timezone.utc)
    dispatch = Dispatch(
        incident_id=incident_id,
        ambulance_id=ambulance_id,
        dispatched_by=user_id,
        status="dispatched",
        dispatched_at=now,
        updated_at=now,
    )
    db.add(dispatch)
    await db.commit()

    fetched = await get_dispatch_by_id(db, dispatch.id)
    try:
        from app.services import response_status_service
        from app.ws.manager import manager
        resp_status = await response_status_service.get_incident_response_status(db, incident_id)
        await manager.broadcast_incident_response_status(resp_status)
    except Exception:
        pass

    return fetched  # type: ignore[return-value]


async def update_dispatch_status(db: AsyncSession, dispatch: Dispatch, new_status: str) -> Dispatch:
    valid_statuses = {"dispatched", "en_route", "arrived", "completed", "cancelled"}
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid dispatch status '{new_status}'. Must be one of {valid_statuses}")

    dispatch.status = new_status
    dispatch.updated_at = datetime.now(timezone.utc)

    # Sync ambulance status
    amb_res = await db.execute(select(Ambulance).where(Ambulance.id == dispatch.ambulance_id))
    ambulance = amb_res.scalar_one_or_none()
    if ambulance:
        if new_status in ("completed", "cancelled"):
            ambulance.status = "available"
        elif new_status == "en_route":
            ambulance.status = "en_route"
        elif new_status == "arrived":
            ambulance.status = "at_scene"
        elif new_status == "dispatched":
            ambulance.status = "dispatched"

    await db.commit()

    fetched = await get_dispatch_by_id(db, dispatch.id)
    try:
        from app.services import response_status_service
        from app.ws.manager import manager
        resp_status = await response_status_service.get_incident_response_status(db, dispatch.incident_id)
        await manager.broadcast_incident_response_status(resp_status)
    except Exception:
        pass

    return fetched  # type: ignore[return-value]


async def get_dispatch_by_id(db: AsyncSession, dispatch_id: uuid.UUID) -> Dispatch | None:
    stmt = (
        select(Dispatch)
        .options(selectinload(Dispatch.ambulance), selectinload(Dispatch.incident))
        .where(Dispatch.id == dispatch_id)
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def list_dispatches(
    db: AsyncSession, incident_id: uuid.UUID | None = None, ambulance_id: uuid.UUID | None = None
) -> list[Dispatch]:
    stmt = (
        select(Dispatch)
        .options(selectinload(Dispatch.ambulance), selectinload(Dispatch.incident))
        .order_by(Dispatch.dispatched_at.desc())
    )
    if incident_id is not None:
        stmt = stmt.where(Dispatch.incident_id == incident_id)
    if ambulance_id is not None:
        stmt = stmt.where(Dispatch.ambulance_id == ambulance_id)

    res = await db.execute(stmt)
    return list(res.scalars().all())


async def get_active_dispatch_for_ambulance(db: AsyncSession, ambulance_id: uuid.UUID) -> Dispatch | None:
    stmt = (
        select(Dispatch)
        .options(selectinload(Dispatch.ambulance), selectinload(Dispatch.incident))
        .where(
            Dispatch.ambulance_id == ambulance_id,
            Dispatch.status.in_(["dispatched", "en_route", "arrived"]),
        )
        .order_by(Dispatch.dispatched_at.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().first()

