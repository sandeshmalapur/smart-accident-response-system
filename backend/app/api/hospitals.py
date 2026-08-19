import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.schemas.hospital import HospitalCreate, HospitalNearestOut, HospitalOut
from app.services import hospital_service

router = APIRouter(prefix="/hospitals", tags=["hospitals"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[HospitalOut])
async def list_hospitals(is_active: bool | None = None, db: AsyncSession = Depends(get_db)) -> list[HospitalOut]:
    hospitals = await hospital_service.list_hospitals(db, is_active=is_active)
    return [HospitalOut.model_validate(h) for h in hospitals]


@router.post("", response_model=HospitalOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
async def create_hospital(data: HospitalCreate, db: AsyncSession = Depends(get_db)) -> HospitalOut:
    hospital = await hospital_service.create_hospital(db, data)
    return HospitalOut.model_validate(hospital)


@router.get("/nearest", response_model=list[HospitalNearestOut])
async def get_nearest_hospitals(
    lat: float, lng: float, limit: int = 3, db: AsyncSession = Depends(get_db)
) -> list[HospitalNearestOut]:
    nearest = await hospital_service.get_nearest_hospitals(db, lat=lat, lng=lng, limit=limit)
    return [HospitalNearestOut(**item) for item in nearest]


@router.get("/{hospital_id}", response_model=HospitalOut)
async def get_hospital(hospital_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> HospitalOut:
    hospital = await hospital_service.get_hospital(db, hospital_id)
    if hospital is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found")
    return HospitalOut.model_validate(hospital)
