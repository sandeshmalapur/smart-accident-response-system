import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import alerts, ambulances, auth, devices, dispatches, hospitals, incidents, readings, welfare_checks, ws
from app.core import welfare_messages
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.mqtt.client import mqtt_subscriber
from app.schemas.welfare_check import WelfareCheckOut
from app.services import welfare_check_service
from app.ws.manager import manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("app.main")


async def _escalation_background_loop():
    while True:
        try:
            await asyncio.sleep(5.0)
            async with AsyncSessionLocal() as db:
                escalated = await welfare_check_service.escalate_expired_welfare_checks(db, timeout_seconds=90.0)
                for check in escalated:
                    out = WelfareCheckOut.model_validate(check).model_dump(mode="json")
                    out["prompt"] = welfare_messages.WELFARE_CHECK_PROMPT
                    out["safety_guidance"] = welfare_messages.SAFETY_GUIDANCE
                    out["escalation_notice"] = welfare_messages.ESCALATION_NOTICE
                    await manager.broadcast_welfare_check(out)
                    logger.info("Escalated expired welfare_check id=%s incident_id=%s", check.id, check.incident_id)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Error in welfare check background escalation loop")


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    mqtt_subscriber.start(loop)
    logger.info("MQTT subscriber started")
    escalation_task = asyncio.create_task(_escalation_background_loop())
    logger.info("Welfare check background escalation loop started")
    yield
    escalation_task.cancel()
    mqtt_subscriber.stop()
    logger.info("MQTT subscriber and escalation loop stopped")


app = FastAPI(title="Smart Accident Response System API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(devices.router, prefix=API_PREFIX)
app.include_router(readings.router, prefix=API_PREFIX)
app.include_router(incidents.router, prefix=API_PREFIX)
app.include_router(hospitals.router, prefix=API_PREFIX)
app.include_router(ambulances.router, prefix=API_PREFIX)
app.include_router(dispatches.router, prefix=API_PREFIX)
app.include_router(welfare_checks.router, prefix=API_PREFIX)
app.include_router(alerts.router, prefix=API_PREFIX)
app.include_router(ws.router, prefix=API_PREFIX)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
