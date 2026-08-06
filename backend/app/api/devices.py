import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.schemas.device import DeviceCreate, DeviceOut
from app.services import device_service

router = APIRouter(prefix="/devices", tags=["devices"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[DeviceOut])
async def list_devices(is_active: bool | None = None, db: AsyncSession = Depends(get_db)) -> list[DeviceOut]:
    devices = await device_service.list_devices(db, is_active=is_active)
    return [DeviceOut.model_validate(d) for d in devices]


@router.post("", response_model=DeviceOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
async def create_device(data: DeviceCreate, db: AsyncSession = Depends(get_db)) -> DeviceOut:
    existing = await device_service.get_device_by_code(db, data.device_code)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="device_code already exists")
    device = await device_service.create_device(db, data)
    return DeviceOut.model_validate(device)


@router.get("/{device_id}", response_model=DeviceOut)
async def get_device(device_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> DeviceOut:
    device = await device_service.get_device(db, device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return DeviceOut.model_validate(device)
