import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import AgencyDispatch, Dispatch, Incident


async def get_incident_response_status(db: AsyncSession, incident_id: uuid.UUID) -> dict:
    inc_res = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = inc_res.scalar_one_or_none()
    if incident is None:
        raise ValueError("Incident not found")

    # Fetch ambulance dispatch
    amb_stmt = (
        select(Dispatch)
        .options(selectinload(Dispatch.ambulance))
        .where(Dispatch.incident_id == incident_id)
        .order_by(Dispatch.dispatched_at.desc())
    )
    amb_res = await db.execute(amb_stmt)
    amb_dispatch = amb_res.scalars().first()

    amb_summary = None
    if amb_dispatch:
        amb_summary = {
            "status": amb_dispatch.status,
            "ambulance_code": amb_dispatch.ambulance.ambulance_code if amb_dispatch.ambulance else None,
        }

    # Fetch agency dispatches (police, fire)
    agency_stmt = (
        select(AgencyDispatch)
        .options(selectinload(AgencyDispatch.agency_unit))
        .where(AgencyDispatch.incident_id == incident_id)
        .order_by(AgencyDispatch.dispatched_at.desc())
    )
    agency_res = await db.execute(agency_stmt)
    agency_dispatches = list(agency_res.scalars().all())

    police_disp = next((d for d in agency_dispatches if d.agency_type == "police" and d.status != "cancelled"), None)
    if police_disp is None:
        police_disp = next((d for d in agency_dispatches if d.agency_type == "police"), None)

    police_summary = None
    if police_disp:
        police_summary = {
            "status": police_disp.status,
            "unit_code": police_disp.agency_unit.unit_code if police_disp.agency_unit else None,
        }

    fire_disp = next((d for d in agency_dispatches if d.agency_type == "fire" and d.status != "cancelled"), None)
    if fire_disp is None:
        fire_disp = next((d for d in agency_dispatches if d.agency_type == "fire"), None)

    fire_summary = None
    if fire_disp:
        fire_summary = {
            "status": fire_disp.status,
            "unit_code": fire_disp.agency_unit.unit_code if fire_disp.agency_unit else None,
        }

    # Calculate overall_status
    responders = [s for s in (amb_summary, police_summary, fire_summary) if s is not None]

    if not responders:
        overall_status = "no_response"
    else:
        statuses = [r["status"] for r in responders]
        all_finished_or_cancelled = all(s in ("completed", "cancelled") for s in statuses)
        has_completed = any(s == "completed" for s in statuses)

        if all_finished_or_cancelled:
            if has_completed:
                overall_status = "resolved"
            else:
                overall_status = "no_response"
        else:
            overall_status = "responding"

    return {
        "incident_id": str(incident_id),
        "ambulance": amb_summary,
        "police": police_summary,
        "fire": fire_summary,
        "overall_status": overall_status,
    }
