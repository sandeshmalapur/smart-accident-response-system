import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device
from app.schemas.device import DeviceCreate


async def list_devices(db: AsyncSession, is_active: bool | None = None) -> list[Device]:
    stmt = select(Device)
    if is_active is not None:
        stmt = stmt.where(Device.is_active == is_active)
    stmt = stmt.order_by(Device.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_device(db: AsyncSession, device_id: uuid.UUID) -> Device | None:
    result = await db.execute(select(Device).where(Device.id == device_id))
    return result.scalar_one_or_none()


async def get_device_by_code(db: AsyncSession, device_code: str) -> Device | None:
    result = await db.execute(select(Device).where(Device.device_code == device_code))
    return result.scalar_one_or_none()


async def create_device(db: AsyncSession, data: DeviceCreate) -> Device:
    device = Device(
        device_code=data.device_code,
        device_type=data.device_type,
        label=data.label,
        owner_name=data.owner_name,
        emergency_contact_name=data.emergency_contact_name,
        emergency_contact_phone=data.emergency_contact_phone,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device

