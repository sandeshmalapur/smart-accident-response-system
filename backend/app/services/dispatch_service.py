import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Ambulance, Dispatch, Incident

logger = logging.getLogger("app.dispatch")


async def _navigate_ambulance_to_incident(
    dispatch_id: uuid.UUID, ambulance_id: uuid.UUID, incident_id: uuid.UUID
) -> None:
    """
    Background runner: moves dispatched ambulance step-by-step toward the incident location,
    automatically transitioning status to 'en_route', updating live coordinates,
    and switching to 'arrived' (at_scene) upon arrival within 50 meters.
    """
    try:
        from app.db.session import AsyncSessionLocal
        from app.schemas.ambulance import AmbulanceOut
        from app.schemas.dispatch import DispatchOut
        from app.services import ambulance_service
        from app.ws.manager import manager

        # Initial delay before en_route
        await asyncio.sleep(2.0)

        # Transition status to en_route
        async with AsyncSessionLocal() as db:
            disp = await get_dispatch_by_id(db, dispatch_id)
            if disp and disp.status == "dispatched":
                await update_dispatch_status(db, disp, "en_route")
                logger.info("Ambulance dispatch %s transitioned to 'en_route'", dispatch_id)

        # Continual movement toward incident
        while True:
            await asyncio.sleep(1.5)
            async with AsyncSessionLocal() as db:
                disp = await get_dispatch_by_id(db, dispatch_id)
                if not disp or disp.status not in ("dispatched", "en_route"):
                    # Arrived, completed, or cancelled
                    break

                amb = await ambulance_service.get_ambulance_by_id(db, ambulance_id)
                inc_res = await db.execute(select(Incident).where(Incident.id == incident_id))
                inc = inc_res.scalar_one_or_none()

                if not amb or not inc or amb.current_latitude is None or amb.current_longitude is None:
                    break

                cur_lat = amb.current_latitude
                cur_lng = amb.current_longitude
                target_lat = inc.latitude
                target_lng = inc.longitude

                d_lat = target_lat - cur_lat
                d_lng = target_lng - cur_lng
                dist_deg = (d_lat**2 + d_lng**2) ** 0.5

                # Threshold distance ~50m (approx 0.00045 degrees)
                if dist_deg <= 0.00045:
                    # Arrived at scene!
                    await ambulance_service.update_ambulance_location(db, amb, lat=target_lat, lng=target_lng)
                    await update_dispatch_status(db, disp, "arrived")
                    logger.info("Ambulance %s ARRIVED at incident scene %s", amb.ambulance_code, incident_id)
                    break

                # Advance toward incident with guaranteed minimum step so it smoothly arrives in ~10-15 steps
                ratio = min(1.0, max(0.20, 0.0008 / dist_deg))
                step_lat = cur_lat + d_lat * ratio
                step_lng = cur_lng + d_lng * ratio

                await ambulance_service.update_ambulance_location(db, amb, lat=step_lat, lng=step_lng)

                await manager.broadcast("ambulance_location", AmbulanceOut.model_validate(amb).model_dump(mode="json"))
                logger.info(
                    "Ambulance %s EN_ROUTE toward (%.5f, %.5f): cur=(%.5f, %.5f) dist_deg=%.5f",
                    amb.ambulance_code,
                    target_lat,
                    target_lng,
                    step_lat,
                    step_lng,
                    dist_deg,
                )

        # Once arrived at incident, keep updating position/status at incident scene automatically
        for _ in range(20):
            await asyncio.sleep(2.5)
            async with AsyncSessionLocal() as db:
                disp = await get_dispatch_by_id(db, dispatch_id)
                if not disp or disp.status != "arrived":
                    break
                amb = await ambulance_service.get_ambulance_by_id(db, ambulance_id)
                if amb:
                    await ambulance_service.update_ambulance_location(db, amb, lat=target_lat, lng=target_lng)
                    await manager.broadcast("ambulance_location", AmbulanceOut.model_validate(amb).model_dump(mode="json"))
    except Exception:
        logger.exception("Error in ambulance navigation runner for dispatch %s", dispatch_id)


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
        from app.schemas.ambulance import AmbulanceOut
        from app.schemas.dispatch import DispatchOut
        from app.services import response_status_service
        from app.ws.manager import manager

        resp_status = await response_status_service.get_incident_response_status(db, incident_id)
        await manager.broadcast_incident_response_status(resp_status)
        if fetched:
            await manager.broadcast("dispatch", DispatchOut.model_validate(fetched).model_dump(mode="json"))
        if ambulance:
            await manager.broadcast("ambulance_location", AmbulanceOut.model_validate(ambulance).model_dump(mode="json"))
    except Exception:
        pass

    # Launch automatic ambulance navigation runner
    asyncio.create_task(_navigate_ambulance_to_incident(dispatch.id, ambulance_id, incident_id))

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
        from app.schemas.ambulance import AmbulanceOut
        from app.schemas.dispatch import DispatchOut
        from app.services import response_status_service
        from app.ws.manager import manager
        resp_status = await response_status_service.get_incident_response_status(db, dispatch.incident_id)
        await manager.broadcast_incident_response_status(resp_status)
        if fetched:
            await manager.broadcast("dispatch", DispatchOut.model_validate(fetched).model_dump(mode="json"))
        if ambulance:
            await manager.broadcast("ambulance_location", AmbulanceOut.model_validate(ambulance).model_dump(mode="json"))
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

