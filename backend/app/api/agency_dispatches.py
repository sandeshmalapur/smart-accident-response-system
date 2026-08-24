import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.agency_dispatch import AgencyDispatchCreate, AgencyDispatchOut, AgencyDispatchUpdate
from app.services import agency_dispatch_service

router = APIRouter(tags=["agency-dispatches"], dependencies=[Depends(get_current_user)])


@router.post(
    "/incidents/{incident_id}/dispatch-agency",
    response_model=AgencyDispatchOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_agency_dispatch(
    incident_id: uuid.UUID,
    data: AgencyDispatchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgencyDispatchOut:
    try:
        dispatch = await agency_dispatch_service.create_agency_dispatch(
            db,
            incident_id=incident_id,
            agency_unit_id=data.agency_unit_id,
            agency_type=data.agency_type,
            user_id=current_user.id,
        )
    except ValueError as exc:
        msg = str(exc)
        if "Incident not found" in msg or "Agency unit not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return AgencyDispatchOut.model_validate(dispatch)


@router.patch("/agency-dispatches/{dispatch_id}", response_model=AgencyDispatchOut)
async def update_agency_dispatch_status(
    dispatch_id: uuid.UUID, data: AgencyDispatchUpdate, db: AsyncSession = Depends(get_db)
) -> AgencyDispatchOut:
    dispatch = await agency_dispatch_service.get_agency_dispatch_by_id(db, dispatch_id)
    if dispatch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency dispatch not found")
    try:
        updated = await agency_dispatch_service.update_agency_dispatch_status(db, dispatch, data.status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return AgencyDispatchOut.model_validate(updated)


@router.get("/agency-dispatches", response_model=list[AgencyDispatchOut])
async def list_agency_dispatches(
    incident_id: uuid.UUID | None = Query(default=None),
    agency_unit_id: uuid.UUID | None = Query(default=None),
    agency_type: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[AgencyDispatchOut]:
    dispatches = await agency_dispatch_service.list_agency_dispatches(
        db, incident_id=incident_id, agency_unit_id=agency_unit_id, agency_type=agency_type
    )
    return [AgencyDispatchOut.model_validate(d) for d in dispatches]


@router.get("/agency-dispatches/{dispatch_id}", response_model=AgencyDispatchOut)
async def get_agency_dispatch(
    dispatch_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> AgencyDispatchOut:
    dispatch = await agency_dispatch_service.get_agency_dispatch_by_id(db, dispatch_id)
    if dispatch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency dispatch not found")
    return AgencyDispatchOut.model_validate(dispatch)
