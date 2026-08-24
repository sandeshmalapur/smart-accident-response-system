import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Incident, IncidentTrackingToken


async def create_tracking_token(
    db: AsyncSession, incident_id: uuid.UUID, expires_in_hours: int = 24
) -> IncidentTrackingToken:
    """
    Generates a secure random tracking token for an incident, valid for expires_in_hours (default 24h).
    """
    token_str = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=expires_in_hours)

    tracking_token = IncidentTrackingToken(
        incident_id=incident_id,
        token=token_str,
        created_at=now,
        expires_at=expires_at,
    )
    db.add(tracking_token)
    await db.commit()
    await db.refresh(tracking_token)
    return tracking_token


async def get_valid_tracking_token(db: AsyncSession, token: str) -> IncidentTrackingToken | None:
    """
    Looks up an incident tracking token and ensures it exists and has not expired.
    """
    stmt = (
        select(IncidentTrackingToken)
        .options(
            selectinload(IncidentTrackingToken.incident).selectinload(Incident.nearest_hospital),
            selectinload(IncidentTrackingToken.incident).selectinload(Incident.device),
        )
        .where(
            IncidentTrackingToken.token == token,
            IncidentTrackingToken.expires_at > datetime.now(timezone.utc),
        )
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()

