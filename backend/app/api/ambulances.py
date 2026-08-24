import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.schemas.ambulance import AmbulanceCreate, AmbulanceNearestOut, AmbulanceOut
from app.schemas.dispatch import DispatchOut
from app.services import ambulance_service, dispatch_service

router = APIRouter(prefix="/ambulances", tags=["ambulances"])


@router.get("", response_model=list[AmbulanceOut], dependencies=[Depends(get_current_user)])
async def list_ambulances(
    status_: str | None = None, db: AsyncSession = Depends(get_db)
) -> list[AmbulanceOut]:
    ambulances = await ambulance_service.list_ambulances(db, status=status_)
    return [AmbulanceOut.model_validate(a) for a in ambulances]


@router.post(
    "",
    response_model=AmbulanceOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_ambulance(data: AmbulanceCreate, db: AsyncSession = Depends(get_db)) -> AmbulanceOut:
    existing = await ambulance_service.get_ambulance_by_code(db, data.ambulance_code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ambulance with code '{data.ambulance_code}' already exists",
        )
    ambulance = await ambulance_service.create_ambulance(db, data)
    return AmbulanceOut.model_validate(ambulance)


@router.get("/nearest", response_model=list[AmbulanceNearestOut], dependencies=[Depends(get_current_user)])
async def get_nearest_ambulances(
    lat: float,
    lng: float,
    status_: str | None = "available",
    limit: int = 3,
    db: AsyncSession = Depends(get_db),
) -> list[AmbulanceNearestOut]:
    nearest = await ambulance_service.get_nearest_ambulances(db, lat=lat, lng=lng, status=status_, limit=limit)
    return [AmbulanceNearestOut(**item) for item in nearest]


@router.get("/{ambulance_identifier}/active-dispatch", response_model=DispatchOut | None)
async def get_ambulance_active_dispatch(
    ambulance_identifier: str, db: AsyncSession = Depends(get_db)
) -> DispatchOut | None:
    try:
        amb_id = uuid.UUID(ambulance_identifier)
        ambulance = await ambulance_service.get_ambulance_by_id(db, amb_id)
    except ValueError:
        ambulance = await ambulance_service.get_ambulance_by_code(db, ambulance_identifier)

    if ambulance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ambulance not found")

    dispatch = await dispatch_service.get_active_dispatch_for_ambulance(db, ambulance.id)
    if dispatch is None:
        return None
    return DispatchOut.model_validate(dispatch)


@router.get("/{ambulance_identifier}", response_model=AmbulanceOut, dependencies=[Depends(get_current_user)])
async def get_ambulance(ambulance_identifier: str, db: AsyncSession = Depends(get_db)) -> AmbulanceOut:
    # Try UUID parse first, fallback to ambulance_code lookup
    try:
        amb_id = uuid.UUID(ambulance_identifier)
        ambulance = await ambulance_service.get_ambulance_by_id(db, amb_id)
    except ValueError:
        ambulance = await ambulance_service.get_ambulance_by_code(db, ambulance_identifier)

    if ambulance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ambulance not found")
    return AmbulanceOut.model_validate(ambulance)

