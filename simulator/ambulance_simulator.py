"""
Ambulance simulator — publishes continuous ambulance location telemetry to MQTT
per MQTT_SPEC.md. Standalone script, mirrors sensor_simulator.py.

Usage examples:
    python simulator/ambulance_simulator.py --ambulance-code AMB-001 --start-lat 12.9716 --start-lng 77.5946
    python simulator/ambulance_simulator.py --ambulance-code AMB-002 --duration 60
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import random
import signal
import sys
import time
from datetime import datetime, timezone
from types import FrameType

from dotenv import load_dotenv
from paho.mqtt import client as mqtt

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [amb-simulator] %(message)s")
logger = logging.getLogger("amb_simulator")

MIN_PUBLISH_INTERVAL_SECONDS = 2.0
MAX_PUBLISH_INTERVAL_SECONDS = 5.0


def parse_args() -> argparse.Namespace:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Publish simulated ambulance location telemetry to MQTT")
    parser.add_argument("--ambulance-code", required=True, help="Must match a registered ambulance_code in backend")
    parser.add_argument("--start-lat", type=float, default=12.9716, help="Initial latitude (default: 12.9716)")
    parser.add_argument("--start-lng", type=float, default=77.5946, help="Initial longitude (default: 77.5946)")
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Seconds to run before stopping automatically. Omit to run until Ctrl+C.",
    )
    parser.add_argument(
        "--broker-host",
        default=os.getenv("MQTT_BROKER_HOST", "localhost"),
        help="MQTT broker host (default: localhost)",
    )
    parser.add_argument(
        "--broker-port",
        type=int,
        default=int(os.getenv("MQTT_BROKER_PORT", "1883")),
        help="MQTT broker port (default: 1883)",
    )
    return parser.parse_args()


def build_location_payload(ambulance_code: str, lat: float, lng: float) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "ambulance_code": ambulance_code,
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z",
        "latitude": round(lat, 6),
        "longitude": round(lng, 6),
    }


class GracefulShutdown:
    def __init__(self) -> None:
        self.requested = False
        signal.signal(signal.SIGINT, self._handle)
        try:
            signal.signal(signal.SIGTERM, self._handle)
        except (ValueError, AttributeError):
            pass

    def _handle(self, signum: int, frame: FrameType | None) -> None:
        logger.info("Shutdown requested (signal %s) — stopping ambulance simulator...", signum)
        self.requested = True


def main() -> int:
    args = parse_args()
    topic = f"ambulance/{args.ambulance_code}/location"

    client = mqtt.Client(
        client_id=f"amb-sim-{args.ambulance_code}-{random.randint(1000, 9999)}",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )

    connected = {"ok": False}

    def on_connect(c, userdata, flags, reason_code, properties=None) -> None:
        failed = getattr(reason_code, "is_failure", None)
        failed = failed if failed is not None else (reason_code != 0)
        if failed:
            logger.error("Failed to connect to broker: %s", reason_code)
            return
        connected["ok"] = True
        logger.info("Connected to broker at %s:%s", args.broker_host, args.broker_port)

    client.on_connect = on_connect

    try:
        client.connect(args.broker_host, args.broker_port, keepalive=60)
    except Exception as exc:
        logger.error("Could not connect to broker at %s:%s — %s", args.broker_host, args.broker_port, exc)
        return 1

    client.loop_start()

    wait_started = time.monotonic()
    while not connected["ok"] and time.monotonic() - wait_started < 5.0:
        time.sleep(0.05)
    if not connected["ok"]:
        logger.error("Timed out waiting for broker connection.")
        client.loop_stop()
        return 1

    shutdown = GracefulShutdown()
    current_lat = args.start_lat
    current_lng = args.start_lng

    logger.info(
        "Simulating location telemetry for ambulance_code='%s' topic='%s' starting at (%.5f, %.5f)",
        args.ambulance_code,
        topic,
        current_lat,
        current_lng,
    )

    start_time = time.monotonic()
    tick = 0
    exit_code = 0

    try:
        while not shutdown.requested:
            if args.duration is not None and (time.monotonic() - start_time) >= args.duration:
                logger.info("Duration elapsed (%ss), stopping.", args.duration)
                break

            payload = build_location_payload(args.ambulance_code, current_lat, current_lng)
            client.publish(topic, json.dumps(payload), qos=1, retain=False)
            logger.info(
                "tick=%d published location lat=%.5f lng=%.5f",
                tick,
                current_lat,
                current_lng,
            )

            # Small realistic random walk step (simulating movement/patrol)
            current_lat += random.uniform(-0.00015, 0.00015)
            current_lng += random.uniform(-0.00015, 0.00015)
            tick += 1

            interval = random.uniform(MIN_PUBLISH_INTERVAL_SECONDS, MAX_PUBLISH_INTERVAL_SECONDS)
            slept = 0.0
            while slept < interval and not shutdown.requested:
                chunk = min(0.1, interval - slept)
                time.sleep(chunk)
                slept += chunk

    except Exception:
        logger.exception("Unexpected error in publish loop")
        exit_code = 1
    finally:
        client.loop_stop()
        client.disconnect()
        logger.info("Disconnected cleanly.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
