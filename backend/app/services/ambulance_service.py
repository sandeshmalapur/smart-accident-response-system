import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Ambulance
from app.schemas.ambulance import AmbulanceCreate
from app.services.hospital_service import haversine_distance


async def list_ambulances(db: AsyncSession, status: str | None = None) -> list[Ambulance]:
    stmt = select(Ambulance)
    if status is not None:
        stmt = stmt.where(Ambulance.status == status)
    stmt = stmt.order_by(Ambulance.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_ambulance_by_id(db: AsyncSession, ambulance_id: uuid.UUID) -> Ambulance | None:
    result = await db.execute(select(Ambulance).where(Ambulance.id == ambulance_id))
    return result.scalar_one_or_none()


async def get_ambulance_by_code(db: AsyncSession, ambulance_code: str) -> Ambulance | None:
    result = await db.execute(select(Ambulance).where(Ambulance.ambulance_code == ambulance_code))
    return result.scalar_one_or_none()


async def create_ambulance(db: AsyncSession, data: AmbulanceCreate) -> Ambulance:
    ambulance = Ambulance(
        ambulance_code=data.ambulance_code,
        label=data.label,
        current_latitude=12.9716,
        current_longitude=77.5946,
        status="available",
        last_location_update=datetime.now(timezone.utc),
    )
    db.add(ambulance)
    await db.commit()
    await db.refresh(ambulance)
    return ambulance


async def update_ambulance_location(
    db: AsyncSession,
    ambulance: Ambulance,
    lat: float,
    lng: float,
    ts: datetime | None = None,
) -> Ambulance:
    ambulance.current_latitude = lat
    ambulance.current_longitude = lng
    ambulance.last_location_update = ts or datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(ambulance)
    return ambulance


async def get_nearest_ambulances(
    db: AsyncSession, lat: float, lng: float, status: str | None = "available", limit: int = 3
) -> list[dict]:
    """
    Fetches ambulances matching status (default available) that have non-null coordinates,
    computes Haversine distance from (lat, lng), and returns top `limit` sorted by distance_km.
    """
    ambulances = await list_ambulances(db, status=status)
    with_distance = []
    for amb in ambulances:
        if amb.current_latitude is not None and amb.current_longitude is not None:
            dist = haversine_distance(lat, lng, amb.current_latitude, amb.current_longitude)
            with_distance.append({
                "ambulance": amb,
                "distance_km": round(dist, 3),
            })

    with_distance.sort(key=lambda x: x["distance_km"])
    top_n = with_distance[:limit]

    result = []
    for item in top_n:
        amb = item["ambulance"]
        result.append({
            "id": amb.id,
            "ambulance_code": amb.ambulance_code,
            "label": amb.label,
            "current_latitude": amb.current_latitude,
            "current_longitude": amb.current_longitude,
            "status": amb.status,
            "last_location_update": amb.last_location_update,
            "created_at": amb.created_at,
            "distance_km": item["distance_km"],
        })
    return result
