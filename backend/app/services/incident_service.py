import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Incident
from app.ml.inference import InferenceResult
from app.schemas.incident import IncidentUpdate


async def list_incidents(
    db: AsyncSession,
    status: str | None = None,
    incident_type: str | None = None,
    device_id: uuid.UUID | None = None,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
    limit: int = 50,
) -> list[Incident]:
    stmt = select(Incident)
    if status is not None:
        stmt = stmt.where(Incident.status == status)
    if incident_type is not None:
        stmt = stmt.where(Incident.incident_type == incident_type)
    if device_id is not None:
        stmt = stmt.where(Incident.device_id == device_id)
    if from_ts is not None:
        stmt = stmt.where(Incident.created_at >= from_ts)
    if to_ts is not None:
        stmt = stmt.where(Incident.created_at <= to_ts)
    stmt = stmt.order_by(Incident.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_incident_detail(db: AsyncSession, incident_id: uuid.UUID) -> Incident | None:
    stmt = (
        select(Incident)
        .where(Incident.id == incident_id)
        .options(selectinload(Incident.sensor_reading), selectinload(Incident.alerts))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_incident(db: AsyncSession, incident_id: uuid.UUID) -> Incident | None:
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    return result.scalar_one_or_none()


async def update_incident_status(db: AsyncSession, incident: Incident, data: IncidentUpdate) -> Incident:
    incident.status = data.status
    if data.status in ("resolved", "false_positive"):
        incident.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(incident)
    return incident


async def create_incident_from_inference(
    db: AsyncSession,
    *,
    device_id: uuid.UUID,
    sensor_reading_id: uuid.UUID,
    latitude: float,
    longitude: float,
    result: InferenceResult,
) -> Incident:
    """
    Persists an incident row when ML inference (app/ml/inference.py) flags
    a reading. Not exposed via REST — incidents are internal-only per
    API_SPEC.md ("incidents are NOT created via REST").
    """
    incident = Incident(
        device_id=device_id,
        sensor_reading_id=sensor_reading_id,
        incident_type=result.incident_type,
        severity=result.severity,
        severity_score=result.severity_score,
        anomaly_score=result.anomaly_score,
        latitude=latitude,
        longitude=longitude,
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    return incident
