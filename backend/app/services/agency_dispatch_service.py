import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import AgencyDispatch, AgencyUnit, Incident
from app.schemas.agency_dispatch import AgencyDispatchOut
from app.schemas.agency_unit import AgencyUnitCreate
from app.services.hospital_service import haversine_distance
from app.ws.manager import manager


async def list_agency_units(
    db: AsyncSession, agency_type: str | None = None, status: str | None = None
) -> list[AgencyUnit]:
    stmt = select(AgencyUnit)
    if agency_type is not None:
        stmt = stmt.where(AgencyUnit.agency_type == agency_type)
    if status is not None:
        stmt = stmt.where(AgencyUnit.status == status)
    stmt = stmt.order_by(AgencyUnit.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_agency_unit_by_id(db: AsyncSession, unit_id: uuid.UUID) -> AgencyUnit | None:
    result = await db.execute(select(AgencyUnit).where(AgencyUnit.id == unit_id))
    return result.scalar_one_or_none()


async def get_agency_unit_by_code(db: AsyncSession, unit_code: str) -> AgencyUnit | None:
    result = await db.execute(select(AgencyUnit).where(AgencyUnit.unit_code == unit_code))
    return result.scalar_one_or_none()


async def create_agency_unit(db: AsyncSession, data: AgencyUnitCreate) -> AgencyUnit:
    unit = AgencyUnit(
        agency_type=data.agency_type,
        unit_code=data.unit_code,
        label=data.label,
        contact_phone=data.contact_phone,
        current_latitude=data.current_latitude,
        current_longitude=data.current_longitude,
        status="available",
    )
    db.add(unit)
    await db.commit()
    await db.refresh(unit)
    return unit


async def get_nearest_agency_units(
    db: AsyncSession,
    agency_type: str,
    lat: float,
    lng: float,
    status: str | None = "available",
    limit: int = 3,
) -> list[dict]:
    stmt = select(AgencyUnit).where(AgencyUnit.agency_type == agency_type)
    if status is not None:
        stmt = stmt.where(AgencyUnit.status == status)
    result = await db.execute(stmt)
    units = list(result.scalars().all())

    scored = []
    for unit in units:
        if unit.current_latitude is None or unit.current_longitude is None:
            continue
        dist = haversine_distance(lat, lng, unit.current_latitude, unit.current_longitude)
        item = {
            "id": unit.id,
            "agency_type": unit.agency_type,
            "unit_code": unit.unit_code,
            "label": unit.label,
            "current_latitude": unit.current_latitude,
            "current_longitude": unit.current_longitude,
            "status": unit.status,
            "last_location_update": unit.last_location_update,
            "created_at": unit.created_at,
            "distance_km": dist,
        }
        scored.append(item)

    scored.sort(key=lambda x: x["distance_km"])
    return scored[:limit]


async def create_agency_dispatch(
    db: AsyncSession,
    incident_id: uuid.UUID,
    agency_unit_id: uuid.UUID,
    agency_type: str,
    user_id: uuid.UUID | None = None,
) -> AgencyDispatch:
    # 1. Fetch incident
    inc_res = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = inc_res.scalar_one_or_none()
    if incident is None:
        raise ValueError("Incident not found")

    # 2. Fetch unit
    unit_res = await db.execute(select(AgencyUnit).where(AgencyUnit.id == agency_unit_id))
    unit = unit_res.scalar_one_or_none()
    if unit is None:
        raise ValueError("Agency unit not found")

    if unit.agency_type != agency_type:
        raise ValueError(
            f"Agency unit is of type '{unit.agency_type}', but dispatch requested '{agency_type}'"
        )

    if unit.status != "available":
        raise ValueError(f"Agency unit status is '{unit.status}', must be 'available' to dispatch")

    # 3. Update unit status
    unit.status = "dispatched"

    # 4. Create dispatch
    now = datetime.now(timezone.utc)
    dispatch = AgencyDispatch(
        incident_id=incident_id,
        agency_unit_id=agency_unit_id,
        dispatched_by=user_id,
        agency_type=agency_type,
        status="pending",
        dispatched_at=now,
        updated_at=now,
    )
    db.add(dispatch)
    await db.commit()

    fetched = await get_agency_dispatch_by_id(db, dispatch.id)
    assert fetched is not None

    # Broadcast over WebSocket
    payload = AgencyDispatchOut.model_validate(fetched).model_dump(mode="json")
    await manager.broadcast_agency_dispatch(payload)
    try:
        from app.services import response_status_service
        resp_status = await response_status_service.get_incident_response_status(db, incident_id)
        await manager.broadcast_incident_response_status(resp_status)
    except Exception:
        pass

    # Trigger agency notification (SMS/mock alert)
    try:
        from app.services import sms_service
        await sms_service.notify_agency_unit(db, fetched, unit, incident)
    except Exception as exc:
        import logging
        logging.getLogger("app.services.agency_dispatch").exception("Failed to dispatch agency unit notification: %s", exc)

    return fetched


async def update_agency_dispatch_status(
    db: AsyncSession, dispatch: AgencyDispatch, new_status: str
) -> AgencyDispatch:
    valid_statuses = {"pending", "en_route", "on_scene", "completed", "cancelled"}
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid agency dispatch status '{new_status}'. Must be one of {valid_statuses}")

    dispatch.status = new_status
    dispatch.updated_at = datetime.now(timezone.utc)

    # Sync unit status
    unit_res = await db.execute(select(AgencyUnit).where(AgencyUnit.id == dispatch.agency_unit_id))
    unit = unit_res.scalar_one_or_none()
    if unit:
        if new_status in ("completed", "cancelled"):
            unit.status = "available"
        elif new_status == "en_route":
            unit.status = "dispatched"
        elif new_status == "on_scene":
            unit.status = "on_scene"
        elif new_status == "pending":
            unit.status = "dispatched"

    await db.commit()

    fetched = await get_agency_dispatch_by_id(db, dispatch.id)
    assert fetched is not None

    # Broadcast over WebSocket
    payload = AgencyDispatchOut.model_validate(fetched).model_dump(mode="json")
    await manager.broadcast_agency_dispatch(payload)
    try:
        from app.services import response_status_service
        resp_status = await response_status_service.get_incident_response_status(db, dispatch.incident_id)
        await manager.broadcast_incident_response_status(resp_status)
    except Exception:
        pass

    return fetched


async def get_agency_dispatch_by_id(db: AsyncSession, dispatch_id: uuid.UUID) -> AgencyDispatch | None:
    stmt = (
        select(AgencyDispatch)
        .options(selectinload(AgencyDispatch.agency_unit), selectinload(AgencyDispatch.incident))
        .where(AgencyDispatch.id == dispatch_id)
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def list_agency_dispatches(
    db: AsyncSession,
    incident_id: uuid.UUID | None = None,
    agency_unit_id: uuid.UUID | None = None,
    agency_type: str | None = None,
) -> list[AgencyDispatch]:
    stmt = (
        select(AgencyDispatch)
        .options(selectinload(AgencyDispatch.agency_unit), selectinload(AgencyDispatch.incident))
        .order_by(AgencyDispatch.dispatched_at.desc())
    )
    if incident_id is not None:
        stmt = stmt.where(AgencyDispatch.incident_id == incident_id)
    if agency_unit_id is not None:
        stmt = stmt.where(AgencyDispatch.agency_unit_id == agency_unit_id)
    if agency_type is not None:
        stmt = stmt.where(AgencyDispatch.agency_type == agency_type)

    res = await db.execute(stmt)
    return list(res.scalars().all())
