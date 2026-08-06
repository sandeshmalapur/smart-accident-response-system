import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import alerts, auth, devices, incidents, readings, ws
from app.core.config import settings
from app.mqtt.client import mqtt_subscriber

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    mqtt_subscriber.start(loop)
    logger.info("MQTT subscriber started")
    yield
    mqtt_subscriber.stop()
    logger.info("MQTT subscriber stopped")


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
app.include_router(alerts.router, prefix=API_PREFIX)
# API_SPEC.md lists all endpoints, including "WS /ws/live", relative to the
# documented Base URL (/api/v1) — so this is mounted at /api/v1/ws/live for
# consistency with every other route in the contract.
app.include_router(ws.router, prefix=API_PREFIX)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
