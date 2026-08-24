import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.schemas.agency_unit import AgencyUnitCreate, AgencyUnitNearestOut, AgencyUnitOut
from app.services import agency_dispatch_service

router = APIRouter(prefix="/agency-units", tags=["agency-units"])


@router.get("", response_model=list[AgencyUnitOut], dependencies=[Depends(get_current_user)])
async def list_agency_units(
    agency_type: str | None = Query(default=None),
    status_: str | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> list[AgencyUnitOut]:
    units = await agency_dispatch_service.list_agency_units(db, agency_type=agency_type, status=status_)
    return [AgencyUnitOut.model_validate(u) for u in units]


@router.post(
    "",
    response_model=AgencyUnitOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_agency_unit(
    data: AgencyUnitCreate, db: AsyncSession = Depends(get_db)
) -> AgencyUnitOut:
    existing = await agency_dispatch_service.get_agency_unit_by_code(db, data.unit_code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agency unit with code '{data.unit_code}' already exists",
        )
    unit = await agency_dispatch_service.create_agency_unit(db, data)
    return AgencyUnitOut.model_validate(unit)


@router.get("/nearest", response_model=list[AgencyUnitNearestOut], dependencies=[Depends(get_current_user)])
async def get_nearest_agency_units(
    agency_type: str = Query(..., description="Required agency type filter (police or fire)"),
    lat: float = Query(...),
    lng: float = Query(...),
    status_: str | None = Query(default="available", alias="status"),
    limit: int = Query(default=3, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> list[AgencyUnitNearestOut]:
    nearest = await agency_dispatch_service.get_nearest_agency_units(
        db, agency_type=agency_type, lat=lat, lng=lng, status=status_, limit=limit
    )
    return [AgencyUnitNearestOut(**item) for item in nearest]


@router.get("/{unit_identifier}", response_model=AgencyUnitOut, dependencies=[Depends(get_current_user)])
async def get_agency_unit(unit_identifier: str, db: AsyncSession = Depends(get_db)) -> AgencyUnitOut:
    try:
        u_id = uuid.UUID(unit_identifier)
        unit = await agency_dispatch_service.get_agency_unit_by_id(db, u_id)
    except ValueError:
        unit = await agency_dispatch_service.get_agency_unit_by_code(db, unit_identifier)

    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency unit not found")
    return AgencyUnitOut.model_validate(unit)
