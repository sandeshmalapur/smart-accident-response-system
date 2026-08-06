import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alert, Incident


async def list_alerts(db: AsyncSession, incident_id: uuid.UUID | None = None, limit: int = 50) -> list[Alert]:
    stmt = select(Alert)
    if incident_id is not None:
        stmt = stmt.where(Alert.incident_id == incident_id)
    stmt = stmt.order_by(Alert.dispatched_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def dispatch_mock_alert(db: AsyncSession, incident: Incident) -> Alert:
    """
    STUB alert dispatch — Phase 1 has no real notification integration
    (PROJECT_CONSTITUTION.md: "notifications are mocked in Phase 1").
    Writes an alerts row with channel="mock", delivery_status="mocked".
    """
    alert = Alert(
        incident_id=incident.id,
        channel="mock",
        recipient=None,
        payload={
            "incident_id": str(incident.id),
            "incident_type": incident.incident_type,
            "severity": incident.severity,
            "latitude": incident.latitude,
            "longitude": incident.longitude,
            "note": "mock dispatch — no real notification integration in Phase 1",
        },
        delivery_status="mocked",
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert
