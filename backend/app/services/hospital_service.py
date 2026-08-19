import math
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Hospital
from app.schemas.hospital import HospitalCreate


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the great-circle distance between two points on Earth 
    in kilometers using the Haversine formula.
    """
    R = 6371.0  # Earth radius in kilometers

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


async def list_hospitals(db: AsyncSession, is_active: bool | None = None) -> list[Hospital]:
    stmt = select(Hospital)
    if is_active is not None:
        stmt = stmt.where(Hospital.is_active == is_active)
    stmt = stmt.order_by(Hospital.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_hospital(db: AsyncSession, hospital_id: uuid.UUID) -> Hospital | None:
    result = await db.execute(select(Hospital).where(Hospital.id == hospital_id))
    return result.scalar_one_or_none()


async def create_hospital(db: AsyncSession, data: HospitalCreate) -> Hospital:
    hospital = Hospital(
        name=data.name,
        latitude=data.latitude,
        longitude=data.longitude,
        phone=data.phone,
    )
    db.add(hospital)
    await db.commit()
    await db.refresh(hospital)
    return hospital


async def get_nearest_hospitals(
    db: AsyncSession, lat: float, lng: float, limit: int = 3
) -> list[dict]:
    """
    Fetches all active hospitals, computes Haversine distance from (lat, lng),
    and returns the top `limit` hospitals sorted by distance (ascending).
    Returns a list of dicts with hospital fields + distance_km.
    """
    hospitals = await list_hospitals(db, is_active=True)
    with_distance = []
    for h in hospitals:
        dist = haversine_distance(lat, lng, h.latitude, h.longitude)
        with_distance.append({
            "hospital": h,
            "distance_km": round(dist, 3),
        })
    with_distance.sort(key=lambda x: x["distance_km"])
    top_n = with_distance[:limit]

    result = []
    for item in top_n:
        h = item["hospital"]
        result.append({
            "id": h.id,
            "name": h.name,
            "latitude": h.latitude,
            "longitude": h.longitude,
            "phone": h.phone,
            "is_active": h.is_active,
            "created_at": h.created_at,
            "distance_km": item["distance_km"],
        })
    return result
