from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import dispatch_service, tracking_service

router = APIRouter(prefix="/track", tags=["tracking"])


class TrackingHospitalOut(BaseModel):
    name: str
    phone: str | None = None

    model_config = {"from_attributes": True}


class TrackingAmbulanceOut(BaseModel):
    label: str | None = None
    current_latitude: float | None = None
    current_longitude: float | None = None
    status: str
    last_location_update: datetime | None = None

    model_config = {"from_attributes": True}


class TrackingDetailOut(BaseModel):
    token: str
    expires_at: datetime
    incident_type: str
    severity: str | None = None
    status: str
    latitude: float
    longitude: float
    created_at: datetime
    owner_name: str | None = None
    hospital: TrackingHospitalOut | None = None
    ambulance: TrackingAmbulanceOut | None = None
    dispatch_status: str | None = None
    dispatched_at: datetime | None = None


@router.get("/{token}", response_model=TrackingDetailOut)
async def get_tracking_detail(token: str, db: AsyncSession = Depends(get_db)) -> TrackingDetailOut:
    """
    Public, unauthenticated endpoint for relative status tracking.
    Lookup incident by token, validating that the token exists and has not expired.
    """
    tracking_token = await tracking_service.get_valid_tracking_token(db, token)
    if tracking_token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tracking link is invalid or has expired",
        )

    incident = tracking_token.incident
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident associated with tracking token not found",
        )

    # Check for active or latest dispatch
    dispatches = await dispatch_service.list_dispatches(db, incident_id=incident.id)
    active_dispatch = None
    if dispatches:
        # Prefer active dispatch (dispatched, en_route, arrived) or latest
        active_dispatch = next(
            (d for d in dispatches if d.status in ("dispatched", "en_route", "arrived")),
            dispatches[0],
        )

    hospital_out = None
    if incident.nearest_hospital:
        hospital_out = TrackingHospitalOut(
            name=incident.nearest_hospital.name,
            phone=incident.nearest_hospital.phone,
        )

    ambulance_out = None
    dispatch_status = None
    dispatched_at = None

    if active_dispatch:
        dispatch_status = active_dispatch.status
        dispatched_at = active_dispatch.dispatched_at
        if active_dispatch.ambulance:
            ambulance_out = TrackingAmbulanceOut(
                label=active_dispatch.ambulance.label,
                current_latitude=active_dispatch.ambulance.current_latitude,
                current_longitude=active_dispatch.ambulance.current_longitude,
                status=active_dispatch.ambulance.status,
                last_location_update=active_dispatch.ambulance.last_location_update,
            )

    owner_name = None
    if incident.device:
        owner_name = incident.device.owner_name

    return TrackingDetailOut(
        token=token,
        expires_at=tracking_token.expires_at,
        incident_type=incident.incident_type,
        severity=incident.severity,
        status=incident.status,
        latitude=incident.latitude,
        longitude=incident.longitude,
        created_at=incident.created_at,
        owner_name=owner_name,
        hospital=hospital_out,
        ambulance=ambulance_out,
        dispatch_status=dispatch_status,
        dispatched_at=dispatched_at,
    )
