import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.incident import IncidentDetailOut, IncidentOut, IncidentUpdate
from app.services import incident_service
from app.ws.manager import manager

router = APIRouter(prefix="/incidents", tags=["incidents"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[IncidentOut])
async def list_incidents(
    status_: str | None = Query(default=None, alias="status"),
    incident_type: str | None = None,
    device_id: uuid.UUID | None = None,
    sensor_reading_id: uuid.UUID | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[IncidentOut]:
    incidents = await incident_service.list_incidents(
        db,
        status=status_,
        incident_type=incident_type,
        device_id=device_id,
        sensor_reading_id=sensor_reading_id,
        from_ts=from_,
        to_ts=to,
        limit=limit,
    )
    return [IncidentOut.model_validate(i) for i in incidents]


@router.get("/{incident_id}", response_model=IncidentDetailOut)
async def get_incident(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> IncidentDetailOut:
    incident = await incident_service.get_incident_detail(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return IncidentDetailOut.model_validate(incident)


@router.patch("/{incident_id}", response_model=IncidentOut)
async def patch_incident(
    incident_id: uuid.UUID, data: IncidentUpdate, db: AsyncSession = Depends(get_db)
) -> IncidentOut:
    incident = await incident_service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    updated = await incident_service.update_incident_status(db, incident, data)
    out = IncidentOut.model_validate(updated)
    await manager.broadcast_incident(out.model_dump(mode="json"))
    return out
