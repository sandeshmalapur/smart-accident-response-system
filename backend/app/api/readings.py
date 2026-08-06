import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.reading import SensorReadingOut
from app.services import reading_service

router = APIRouter(prefix="/readings", tags=["readings"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[SensorReadingOut])
async def list_readings(
    device_id: uuid.UUID | None = None,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    limit: int = Query(default=100, le=1000),
    db: AsyncSession = Depends(get_db),
) -> list[SensorReadingOut]:
    readings = await reading_service.list_readings(db, device_id=device_id, from_ts=from_, to_ts=to, limit=limit)
    return [SensorReadingOut.model_validate(r) for r in readings]


@router.get("/latest", response_model=list[SensorReadingOut])
async def latest_readings(
    device_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[SensorReadingOut]:
    readings = await reading_service.latest_readings(db, device_id=device_id)
    return [SensorReadingOut.model_validate(r) for r in readings]
