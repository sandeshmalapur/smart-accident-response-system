"""
MQTT subscriber per MQTT_SPEC.md.

Subscribes to safe/+/telemetry and safe/+/status (QoS 1, wildcard across
devices). On telemetry: validate schema -> resolve device_code -> persist
sensor_readings -> run ML stub -> broadcast over /ws/live. Malformed
payloads are logged and dropped, never crash the subscriber.

Device online/offline state (from `status` messages) is NOT in
DATABASE_SCHEMA.md yet. MQTT_SPEC.md explicitly allows "in-memory or
lightweight table — not yet in DATABASE_SCHEMA.md, add if needed."
Since the 5-table schema is frozen for this sprint, this keeps it
in-memory (`_device_status`) rather than adding a table. Flagged in the
sprint report — revisit if the dashboard needs this persisted.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone

from paho.mqtt import client as mqtt

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.ml.inference import run_inference
from app.schemas.reading import MqttStatusPayload, MqttTelemetryPayload
from app.services import alert_service, device_service, incident_service, reading_service
from app.ws.manager import manager

logger = logging.getLogger("app.mqtt")

TELEMETRY_TOPIC_FILTER = "safe/+/telemetry"
STATUS_TOPIC_FILTER = "safe/+/status"


class MqttSubscriber:
    def __init__(self) -> None:
        self._client = mqtt.Client(
            client_id=settings.mqtt_client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect
        self._loop: asyncio.AbstractEventLoop | None = None
        # In-memory last-seen device status (see module docstring).
        self._device_status: dict[str, dict] = {}

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        try:
            self._client.connect(settings.mqtt_broker_host, settings.mqtt_broker_port, settings.mqtt_keepalive)
        except Exception:
            logger.exception("MQTT initial connect failed; will keep retrying in background")
        self._client.loop_start()

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    def get_device_status(self, device_code: str) -> dict | None:
        return self._device_status.get(device_code)

    # --- paho callbacks (run on paho's network thread, NOT the asyncio loop) ---

    def _on_connect(self, client: mqtt.Client, userdata, flags, reason_code, properties=None) -> None:
        failed = getattr(reason_code, "is_failure", None)
        failed = failed if failed is not None else (reason_code != 0)
        if failed:
            logger.error("MQTT connect failed: %s", reason_code)
            return
        logger.info("MQTT connected to %s:%s", settings.mqtt_broker_host, settings.mqtt_broker_port)
        client.subscribe(TELEMETRY_TOPIC_FILTER, qos=1)
        client.subscribe(STATUS_TOPIC_FILTER, qos=1)

    def _on_disconnect(self, client: mqtt.Client, userdata, flags, reason_code, properties=None) -> None:
        logger.warning("MQTT disconnected: %s", reason_code)

    def _on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:
        if self._loop is None:
            return
        # Hop from paho's thread onto the FastAPI asyncio loop.
        asyncio.run_coroutine_threadsafe(self._handle_message(msg.topic, msg.payload), self._loop)

    # --- async handling on the FastAPI event loop ---

    async def _handle_message(self, topic: str, raw_payload: bytes) -> None:
        try:
            data = json.loads(raw_payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("Dropped malformed (non-JSON) message on topic %s", topic)
            return

        try:
            if topic.endswith("/telemetry"):
                await self._handle_telemetry(data)
            elif topic.endswith("/status"):
                await self._handle_status(data)
            else:
                logger.warning("Message on unrecognized topic %s ignored", topic)
        except Exception:
            # Never let a bad message crash the subscriber.
            logger.exception("Error handling message on topic %s", topic)

    async def _handle_telemetry(self, data: dict) -> None:
        try:
            payload = MqttTelemetryPayload.model_validate(data)
        except Exception as exc:
            logger.warning("Dropped malformed telemetry payload: %s", exc)
            return

        async with AsyncSessionLocal() as db:
            device = await device_service.get_device_by_code(db, payload.device_code)
            if device is None:
                logger.warning("Dropped telemetry for unknown device_code=%s", payload.device_code)
                return

            reading = await reading_service.create_reading(db, device.id, payload)
            logger.info("Persisted sensor_reading id=%s device_code=%s", reading.id, payload.device_code)

            from app.schemas.reading import SensorReadingOut

            reading_out = SensorReadingOut.model_validate(reading).model_dump(mode="json")
            await manager.broadcast_reading(reading_out)

            # ML stub (Sprint S3 replaces this with real SVM/GMM inference).
            result = run_inference(
                accel_x=reading.accel_x,
                accel_y=reading.accel_y,
                accel_z=reading.accel_z,
                gyro_x=reading.gyro_x,
                gyro_y=reading.gyro_y,
                gyro_z=reading.gyro_z,
                gas_level=reading.gas_level,
            )
            if result.is_incident:
                incident = await incident_service.create_incident_from_inference(
                    db,
                    device_id=device.id,
                    sensor_reading_id=reading.id,
                    latitude=reading.latitude,
                    longitude=reading.longitude,
                    result=result,
                )
                from app.schemas.incident import IncidentOut

                await manager.broadcast_incident(IncidentOut.model_validate(incident).model_dump(mode="json"))

                alert = await alert_service.dispatch_mock_alert(db, incident)
                from app.schemas.alert import AlertOut

                await manager.broadcast_alert(AlertOut.model_validate(alert).model_dump(mode="json"))

    async def _handle_status(self, data: dict) -> None:
        try:
            payload = MqttStatusPayload.model_validate(data)
        except Exception as exc:
            logger.warning("Dropped malformed status payload: %s", exc)
            return

        self._device_status[payload.device_code] = {
            "status": payload.status,
            "timestamp": payload.timestamp,
            "last_seen": datetime.now(timezone.utc),
        }
        logger.info("Device status update: %s -> %s", payload.device_code, payload.status)


mqtt_subscriber = MqttSubscriber()
