import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SensorReading
from app.schemas.reading import MqttTelemetryPayload


async def list_readings(
    db: AsyncSession,
    device_id: uuid.UUID | None = None,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
    limit: int = 100,
) -> list[SensorReading]:
    stmt = select(SensorReading)
    if device_id is not None:
        stmt = stmt.where(SensorReading.device_id == device_id)
    if from_ts is not None:
        stmt = stmt.where(SensorReading.recorded_at >= from_ts)
    if to_ts is not None:
        stmt = stmt.where(SensorReading.recorded_at <= to_ts)
    stmt = stmt.order_by(SensorReading.recorded_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def latest_readings(db: AsyncSession, device_id: uuid.UUID | None = None) -> list[SensorReading]:
    """
    Latest reading overall for a device, or latest-per-device if device_id
    is omitted (one row per distinct device_id).
    """
    if device_id is not None:
        stmt = (
            select(SensorReading)
            .where(SensorReading.device_id == device_id)
            .order_by(SensorReading.recorded_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return [row] if row else []

    # Latest per device: window function via DISTINCT ON (Postgres-specific,
    # fine here since Postgres/Supabase is the locked engine).
    stmt = (
        select(SensorReading)
        .distinct(SensorReading.device_id)
        .order_by(SensorReading.device_id, SensorReading.recorded_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_reading(db: AsyncSession, device_id: uuid.UUID, payload: MqttTelemetryPayload) -> SensorReading:
    reading = SensorReading(
        device_id=device_id,
        accel_x=payload.accel.x,
        accel_y=payload.accel.y,
        accel_z=payload.accel.z,
        gyro_x=payload.gyro.x if payload.gyro else None,
        gyro_y=payload.gyro.y if payload.gyro else None,
        gyro_z=payload.gyro.z if payload.gyro else None,
        gas_level=payload.gas_level,
        latitude=payload.gps.lat,
        longitude=payload.gps.lng,
        recorded_at=payload.recorded_at,
    )
    db.add(reading)
    await db.commit()
    await db.refresh(reading)
    return reading
