"""
Manual MQTT Telemetry Input Tool (Temporary testing utility)

Allows typing in raw sensor values (accel, gyro, gas_level, gps) by hand
and publishing single reading payloads to MQTT for edge case testing.

Usage:
    python simulator/manual_input.py
"""
import json
import math
import os
import random
import signal
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from paho.mqtt import client as mqtt


def get_timestamp_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def build_status_payload(device_code: str, status: str) -> dict:
    return {
        "device_code": device_code,
        "status": status,
        "timestamp": get_timestamp_iso(),
    }


def prompt_float(field_name: str, current_value: float) -> float:
    while True:
        try:
            val_str = input(f"  {field_name} [{current_value}]: ").strip()
            if not val_str:
                return current_value
            return float(val_str)
        except (ValueError, TypeError):
            print(f"    [Error] Invalid number for {field_name}. Please enter a valid float.")


def main() -> int:
    load_dotenv()
    print("==================================================")
    print("   Manual MQTT Telemetry Input Tool (Dev Utility)  ")
    print("==================================================")

    # Initial device & broker prompts
    default_device = "SIM-001"
    default_host = os.getenv("MQTT_BROKER_HOST", "localhost")
    default_port = int(os.getenv("MQTT_BROKER_PORT", "1883"))

    device_code = input(f"Device code [{default_device}]: ").strip() or default_device
    broker_host = input(f"MQTT Broker Host [{default_host}]: ").strip() or default_host
    
    port_input = input(f"MQTT Broker Port [{default_port}]: ").strip()
    try:
        broker_port = int(port_input) if port_input else default_port
    except ValueError:
        print(f"Invalid port '{port_input}', using default {default_port}")
        broker_port = default_port

    status_topic = f"safe/{device_code}/status"
    telemetry_topic = f"safe/{device_code}/telemetry"

    # MQTT Client setup
    client = mqtt.Client(
        client_id=f"manual-input-{device_code}-{random.randint(1000, 9999)}",
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )

    connected = {"ok": False}

    def on_connect(c, userdata, flags, reason_code, properties=None) -> None:
        failed = getattr(reason_code, "is_failure", None)
        failed = failed if failed is not None else (reason_code != 0)
        if failed:
            print(f"Failed to connect to MQTT broker: {reason_code}")
            return
        connected["ok"] = True

    client.on_connect = on_connect

    try:
        client.connect(broker_host, broker_port, keepalive=60)
    except Exception as exc:
        print(f"\n[Error] Could not connect to MQTT broker at {broker_host}:{broker_port} — {exc}")
        print("Is Mosquitto running? Try: docker compose up -d postgres mosquitto")
        return 1

    client.loop_start()

    wait_started = time.monotonic()
    while not connected["ok"] and time.monotonic() - wait_started < 5.0:
        time.sleep(0.05)

    if not connected["ok"]:
        print("\n[Error] Timed out waiting for MQTT broker connection.")
        client.loop_stop()
        return 1

    print(f"\nConnected to MQTT broker at {broker_host}:{broker_port}")

    # Publish online status
    client.publish(status_topic, json.dumps(build_status_payload(device_code, "online")), qos=1, retain=False)
    print(f"Published online status to {status_topic}\n")

    # Initial telemetry field defaults
    values = {
        "accel_x": 0.0,
        "accel_y": 0.0,
        "accel_z": 9.81,
        "gyro_x": 0.0,
        "gyro_y": 0.0,
        "gyro_z": 0.0,
        "gas_level": 105.0,
        "latitude": 12.9141,
        "longitude": 74.8560,
    }

    def cleanup():
        print("\nPublishing offline status and disconnecting...")
        try:
            client.publish(
                status_topic, json.dumps(build_status_payload(device_code, "offline")), qos=1, retain=False
            )
            time.sleep(0.3)
        except Exception:
            pass
        finally:
            client.loop_stop()
            client.disconnect()
            print("Disconnected cleanly.")

    try:
        while True:
            print("--- Enter Telemetry Values ---")
            values["accel_x"] = prompt_float("accel_x", values["accel_x"])
            values["accel_y"] = prompt_float("accel_y", values["accel_y"])
            values["accel_z"] = prompt_float("accel_z", values["accel_z"])

            values["gyro_x"] = prompt_float("gyro_x", values["gyro_x"])
            values["gyro_y"] = prompt_float("gyro_y", values["gyro_y"])
            values["gyro_z"] = prompt_float("gyro_z", values["gyro_z"])

            values["gas_level"] = prompt_float("gas_level", values["gas_level"])

            values["latitude"] = prompt_float("latitude", values["latitude"])
            values["longitude"] = prompt_float("longitude", values["longitude"])

            # Compute acceleration magnitude
            accel_mag = math.sqrt(values["accel_x"] ** 2 + values["accel_y"] ** 2 + values["accel_z"] ** 2)

            # Build telemetry payload matching MQTT_SPEC.md
            payload = {
                "device_code": device_code,
                "recorded_at": get_timestamp_iso(),
                "accel": {
                    "x": round(values["accel_x"], 4),
                    "y": round(values["accel_y"], 4),
                    "z": round(values["accel_z"], 4),
                },
                "gyro": {
                    "x": round(values["gyro_x"], 4),
                    "y": round(values["gyro_y"], 4),
                    "z": round(values["gyro_z"], 4),
                },
                "gas_level": round(values["gas_level"], 2),
                "gps": {
                    "lat": round(values["latitude"], 6),
                    "lng": round(values["longitude"], 6),
                },
            }

            client.publish(telemetry_topic, json.dumps(payload), qos=1, retain=False)
            print(f"\n>> Published to {telemetry_topic}. accel_magnitude={accel_mag:.2f}\n")

            again = input("Publish another? [Y/n]: ").strip().lower()
            if again and again.startswith("n"):
                break
            print()

    except (KeyboardInterrupt, EOFError):
        print("\n[Ctrl+C detected]")
    finally:
        cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main())
