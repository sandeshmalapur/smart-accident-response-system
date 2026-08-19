import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.dispatch import DispatchCreate, DispatchOut, DispatchUpdate
from app.services import dispatch_service

router = APIRouter(tags=["dispatches"], dependencies=[Depends(get_current_user)])


@router.post("/incidents/{incident_id}/dispatch", response_model=DispatchOut, status_code=status.HTTP_201_CREATED)
async def create_dispatch(
    incident_id: uuid.UUID,
    data: DispatchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DispatchOut:
    try:
        dispatch = await dispatch_service.create_dispatch(
            db, incident_id=incident_id, ambulance_id=data.ambulance_id, user_id=current_user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return DispatchOut.model_validate(dispatch)


@router.patch("/dispatches/{dispatch_id}", response_model=DispatchOut)
async def update_dispatch_status(
    dispatch_id: uuid.UUID, data: DispatchUpdate, db: AsyncSession = Depends(get_db)
) -> DispatchOut:
    dispatch = await dispatch_service.get_dispatch_by_id(db, dispatch_id)
    if dispatch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispatch not found")
    try:
        updated = await dispatch_service.update_dispatch_status(db, dispatch, data.status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return DispatchOut.model_validate(updated)


@router.get("/dispatches", response_model=list[DispatchOut])
async def list_dispatches(
    incident_id: uuid.UUID | None = Query(default=None),
    ambulance_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[DispatchOut]:
    dispatches = await dispatch_service.list_dispatches(db, incident_id=incident_id, ambulance_id=ambulance_id)
    return [DispatchOut.model_validate(d) for d in dispatches]


@router.get("/dispatches/{dispatch_id}", response_model=DispatchOut)
async def get_dispatch(dispatch_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> DispatchOut:
    dispatch = await dispatch_service.get_dispatch_by_id(db, dispatch_id)
    if dispatch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispatch not found")
    return DispatchOut.model_validate(dispatch)
