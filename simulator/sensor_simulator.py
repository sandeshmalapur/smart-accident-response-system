"""
Sensor simulator — publishes fake telemetry + status to MQTT per
MQTT_SPEC.md, mimicking a real ESP32 device. Standalone script, does not
touch backend/, frontend/, or ml/.

Usage examples:
    python simulator/sensor_simulator.py --device-code SIM-001
    python simulator/sensor_simulator.py --device-code SIM-001 --scenario severe_crash --duration 30
    python simulator/sensor_simulator.py --device-code SIM-001 --scenario gas_leak --duration 60
    python simulator/sensor_simulator.py --device-code SIM-001 --broker-host 192.168.1.50 --broker-port 1883

See README.md for how to seed a test device in the backend first — the
backend drops telemetry for any device_code it doesn't recognize.
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

from scenarios import SCENARIOS, get_scenario

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [simulator] %(message)s")
logger = logging.getLogger("simulator")

STATUS_HEARTBEAT_SECONDS = 30.0
MIN_PUBLISH_INTERVAL_SECONDS = 0.2
MAX_PUBLISH_INTERVAL_SECONDS = 1.0


def parse_args() -> argparse.Namespace:
    load_dotenv()  # allows a simulator/.env to supply defaults

    parser = argparse.ArgumentParser(description="Publish simulated sensor telemetry to MQTT per MQTT_SPEC.md")
    parser.add_argument("--device-code", required=True, help="Must already exist in the backend's devices table")
    parser.add_argument(
        "--scenario",
        default="normal",
        choices=sorted(SCENARIOS),
        help="Which scenario to run (default: normal)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Seconds to run before stopping automatically. Omit to run until Ctrl+C.",
    )
    parser.add_argument(
        "--broker-host",
        default=os.getenv("MQTT_BROKER_HOST", "localhost"),
        help="MQTT broker host (default: localhost, or $MQTT_BROKER_HOST)",
    )
    parser.add_argument(
        "--broker-port",
        type=int,
        default=int(os.getenv("MQTT_BROKER_PORT", "1883")),
        help="MQTT broker port (default: 1883, or $MQTT_BROKER_PORT)",
    )
    parser.add_argument(
        "--min-interval",
        type=float,
        default=MIN_PUBLISH_INTERVAL_SECONDS,
        help="Minimum seconds between telemetry publishes (default: 0.2, per MQTT_SPEC.md)",
    )
    parser.add_argument(
        "--max-interval",
        type=float,
        default=MAX_PUBLISH_INTERVAL_SECONDS,
        help="Maximum seconds between telemetry publishes (default: 1.0, per MQTT_SPEC.md)",
    )
    return parser.parse_args()


def build_telemetry_payload(device_code: str, sample) -> dict:
    """Matches MQTT_SPEC.md's telemetry payload shape exactly."""
    now = datetime.now(timezone.utc)
    return {
        "device_code": device_code,
        "recorded_at": now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z",
        "accel": {"x": round(sample.accel[0], 4), "y": round(sample.accel[1], 4), "z": round(sample.accel[2], 4)},
        "gyro": {"x": round(sample.gyro[0], 4), "y": round(sample.gyro[1], 4), "z": round(sample.gyro[2], 4)},
        "gas_level": round(sample.gas_level, 2),
        "gps": {"lat": round(sample.lat, 6), "lng": round(sample.lng, 6)},
    }


def build_status_payload(device_code: str, status: str) -> dict:
    """Matches MQTT_SPEC.md's status payload shape exactly."""
    now = datetime.now(timezone.utc)
    return {
        "device_code": device_code,
        "status": status,
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z",
    }


class GracefulShutdown:
    """Tracks whether SIGINT/SIGTERM has been requested, without raising mid-publish."""

    def __init__(self) -> None:
        self.requested = False
        signal.signal(signal.SIGINT, self._handle)
        try:
            signal.signal(signal.SIGTERM, self._handle)
        except (ValueError, AttributeError):
            pass  # SIGTERM not available on this platform (e.g. some Windows setups)

    def _handle(self, signum: int, frame: FrameType | None) -> None:
        logger.info("Shutdown requested (signal %s) — publishing offline status and stopping...", signum)
        self.requested = True


def main() -> int:
    args = parse_args()

    status_topic = f"safe/{args.device_code}/status"
    telemetry_topic = f"safe/{args.device_code}/telemetry"

    client = mqtt.Client(
        client_id=f"simulator-{args.device_code}-{random.randint(1000, 9999)}",
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
        logger.error("Is Mosquitto running? Try: docker compose up -d postgres mosquitto")
        return 1

    client.loop_start()

    # Give the connect handshake a moment to complete before publishing.
    wait_started = time.monotonic()
    while not connected["ok"] and time.monotonic() - wait_started < 5.0:
        time.sleep(0.05)
    if not connected["ok"]:
        logger.error("Timed out waiting for broker connection.")
        client.loop_stop()
        return 1

    shutdown = GracefulShutdown()

    # Announce online.
    client.publish(status_topic, json.dumps(build_status_payload(args.device_code, "online")), qos=1, retain=False)
    logger.info("Published online status to %s", status_topic)

    scenario = get_scenario(args.scenario)
    logger.info(
        "Running scenario='%s' for device_code='%s' (duration=%s)",
        args.scenario,
        args.device_code,
        f"{args.duration}s" if args.duration is not None else "until Ctrl+C",
    )

    tick = 0
    start_time = time.monotonic()
    last_heartbeat = time.monotonic()
    exit_code = 0

    try:
        while not shutdown.requested:
            if args.duration is not None and (time.monotonic() - start_time) >= args.duration:
                logger.info("Duration elapsed, stopping.")
                break

            sample = scenario.next_reading(tick)
            payload = build_telemetry_payload(args.device_code, sample)
            client.publish(telemetry_topic, json.dumps(payload), qos=1, retain=False)
            logger.info(
                "tick=%d accel=(%.2f,%.2f,%.2f) gas=%.1f gps=(%.5f,%.5f)",
                tick,
                sample.accel[0],
                sample.accel[1],
                sample.accel[2],
                sample.gas_level,
                sample.lat,
                sample.lng,
            )
            tick += 1

            now = time.monotonic()
            if now - last_heartbeat >= STATUS_HEARTBEAT_SECONDS:
                client.publish(
                    status_topic, json.dumps(build_status_payload(args.device_code, "online")), qos=1, retain=False
                )
                logger.info("Published heartbeat status to %s", status_topic)
                last_heartbeat = now

            interval = random.uniform(args.min_interval, args.max_interval)
            # Sleep in small chunks so Ctrl+C is responsive even mid-interval.
            slept = 0.0
            while slept < interval and not shutdown.requested:
                chunk = min(0.1, interval - slept)
                time.sleep(chunk)
                slept += chunk
    except Exception:
        logger.exception("Unexpected error in publish loop")
        exit_code = 1
    finally:
        try:
            client.publish(
                status_topic, json.dumps(build_status_payload(args.device_code, "offline")), qos=1, retain=False
            )
            logger.info("Published offline status to %s", status_topic)
            time.sleep(0.3)  # give the QoS-1 publish a moment to actually leave before disconnecting
        finally:
            client.loop_stop()
            client.disconnect()
            logger.info("Disconnected cleanly.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
