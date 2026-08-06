import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.alert import AlertOut
from app.services import alert_service

router = APIRouter(prefix="/alerts", tags=["alerts"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    incident_id: uuid.UUID | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[AlertOut]:
    alerts = await alert_service.list_alerts(db, incident_id=incident_id, limit=limit)
    return [AlertOut.model_validate(a) for a in alerts]
