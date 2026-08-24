"""
SMS Service — Twilio integration wrapper.

Note on Twilio Trial Accounts:
This service uses Twilio for SMS notifications. On a Twilio Trial account,
SMS messages can ONLY be delivered to phone numbers that are explicitly verified
in the Twilio Console for that trial account. Attempting to send to unverified numbers
or using unconfigured credentials will log a warning and return False cleanly without crashing.
"""
import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgencyDispatch, AgencyUnit, Alert, Incident

logger = logging.getLogger("sms_service")


def send_accident_alert_sms(phone: str, owner_name: str | None, token: str) -> bool:
    """
    Sends an SMS alert with a public trackable link to the emergency contact phone number.
    Returns True if successfully dispatched via Twilio, False otherwise.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()
    frontend_url = os.getenv("FRONTEND_BASE_URL", os.getenv("TRACKING_BASE_URL", "http://localhost:5173")).rstrip("/")

    tracking_link_url = f"{frontend_url}/track/{token}"
    name_str = owner_name.strip() if owner_name and owner_name.strip() else "Vehicle"
    message_body = f"{name_str}'s vehicle was involved in a possible accident. Track live status: {tracking_link_url}"

    if not account_sid or not auth_token or not from_number:
        logger.warning(
            "Twilio SMS credentials missing or incomplete (ACCOUNT_SID/AUTH_TOKEN/FROM_NUMBER) — "
            "skipping SMS dispatch to %s. Intended SMS body: %s",
            phone,
            message_body,
        )
        return False

    try:
        from twilio.rest import Client  # type: ignore

        client = Client(account_sid, auth_token)
        msg = client.messages.create(
            body=message_body,
            from_=from_number,
            to=phone,
        )
        logger.info("Successfully dispatched SMS alert to %s (SID: %s)", phone, msg.sid)
        return True
    except Exception as exc:
        logger.error(
            "Failed to send SMS to %s via Twilio (Note: Trial accounts can only send to verified numbers): %s",
            phone,
            exc,
        )
        return False


async def notify_agency_unit(
    db: AsyncSession,
    dispatch: AgencyDispatch,
    agency_unit: AgencyUnit,
    incident: Incident,
) -> Alert:
    """
    Notifies an agency unit when assigned to an incident.
    Sends SMS if Twilio is configured and phone is present; otherwise creates a mock Alert row.
    Never throws an unhandled exception to prevent rolling back dispatch creation.
    """
    message_body = (
        f"[EMERGENCY DISPATCH] Unit {agency_unit.unit_code} ({agency_unit.agency_type.upper()}) "
        f"assigned to {incident.incident_type} (severity: {incident.severity or 'N/A'}) "
        f"at lat={incident.latitude}, lng={incident.longitude}."
    )

    phone = agency_unit.contact_phone
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()

    channel = "mock"
    delivery_status = "mocked"

    if phone and account_sid and auth_token and from_number:
        try:
            from twilio.rest import Client  # type: ignore

            client = Client(account_sid, auth_token)
            client.messages.create(
                body=message_body,
                from_=from_number,
                to=phone,
            )
            channel = "sms"
            delivery_status = "sent"
            logger.info("Successfully sent SMS notification to agency unit %s", agency_unit.unit_code)
        except Exception as exc:
            logger.warning("Twilio SMS send failed for agency unit %s: %s", agency_unit.unit_code, exc)

    alert = Alert(
        incident_id=incident.id,
        channel=channel,
        recipient=phone or agency_unit.unit_code,
        payload={
            "unit_code": agency_unit.unit_code,
            "agency_type": agency_unit.agency_type,
            "severity": incident.severity,
            "incident_type": incident.incident_type,
            "latitude": incident.latitude,
            "longitude": incident.longitude,
            "message": message_body,
        },
        delivery_status=delivery_status,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert
