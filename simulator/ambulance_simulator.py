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
import math
import os
import random
import signal
import sys
import time
import urllib.error
import urllib.request
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
        "--backend-url",
        default=os.getenv("BACKEND_URL", "http://localhost:8000"),
        help="Backend API base URL (default: http://localhost:8000)",
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


def fetch_active_dispatch(backend_url: str, ambulance_code: str) -> dict | None:
    url = f"{backend_url.rstrip('/')}/api/v1/ambulances/{ambulance_code}/active-dispatch"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AmbulanceSimulator/1.0"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status == 200:
                content = resp.read()
                if not content:
                    return None
                data = json.loads(content.decode("utf-8"))
                if data and isinstance(data, dict) and data.get("incident"):
                    return data
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        logger.debug("HTTP error fetching active dispatch: %s", exc)
    except Exception as exc:
        logger.debug("Error fetching active dispatch: %s", exc)
    return None


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

            active_dispatch = fetch_active_dispatch(args.backend_url, args.ambulance_code)

            payload = build_location_payload(args.ambulance_code, current_lat, current_lng)
            client.publish(topic, json.dumps(payload), qos=1, retain=False)

            if active_dispatch and active_dispatch.get("incident"):
                incident = active_dispatch["incident"]
                target_lat = incident["latitude"]
                target_lng = incident["longitude"]

                d_lat = target_lat - current_lat
                d_lng = target_lng - current_lng
                dist_deg = (d_lat**2 + d_lng**2) ** 0.5

                # Threshold distance ~50m (approx 0.00045 degrees)
                if dist_deg <= 0.00045:
                    logger.info(
                        "tick=%d [DISPATCHED] Arrived near incident target=(%.5f, %.5f) cur=(%.5f, %.5f) dist=%.6f deg. Holding position.",
                        tick,
                        target_lat,
                        target_lng,
                        current_lat,
                        current_lng,
                        dist_deg,
                    )
                else:
                    current_lat += d_lat * 0.18
                    current_lng += d_lng * 0.18
                    logger.info(
                        "tick=%d [DISPATCHED] Moving toward incident target=(%.5f, %.5f) cur=(%.5f, %.5f) dist=%.6f deg",
                        tick,
                        target_lat,
                        target_lng,
                        current_lat,
                        current_lng,
                        dist_deg,
                    )
            else:
                heading = tick * 0.35
                current_lat += 0.0010 * math.cos(heading)
                current_lng += 0.0010 * math.sin(heading)
                logger.info(
                    "tick=%d [PATROLLING] published location lat=%.5f lng=%.5f",
                    tick,
                    current_lat,
                    current_lng,
                )

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
