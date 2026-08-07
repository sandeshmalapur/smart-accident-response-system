"""Manual test harness for InferenceService -- lets you type in a sensor
reading (or pass one via CLI flags) and see what the models predict, without
writing a Python one-liner each time.

This is a dev/QA convenience only -- it is NOT part of what gets dropped
into backend/app/ml/inference.py. In production, the backend's MQTT
subscriber calls InferenceService directly with parsed telemetry payloads.

Usage examples:
    # Interactive prompts:
    python check_model.py

    # One-shot via flags (skip prompts):
    python check_model.py --accel 10 7 5 --gyro 70 -65 50 --gas 850

    # Severity only, no gyro (device didn't report it):
    python check_model.py --accel 0.1 -0.2 0.05 --gas 200
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from inference import InferenceService


def _prompt_float(label: str, default: float) -> float:
    raw = input(f"{label} [{default}]: ").strip()
    return float(raw) if raw else default


def _prompt_triplet(label: str, default: tuple[float, float, float]) -> dict:
    raw = input(f"{label} x y z [{default[0]} {default[1]} {default[2]}]: ").strip()
    if not raw:
        return {"x": default[0], "y": default[1], "z": default[2]}
    x, y, z = (float(v) for v in raw.split())
    return {"x": x, "y": y, "z": z}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--accel", type=float, nargs=3, metavar=("X", "Y", "Z"), help="accel x y z (m/s^2)")
    parser.add_argument("--gyro", type=float, nargs=3, metavar=("X", "Y", "Z"), help="gyro x y z (deg/s), omit if not simulated")
    parser.add_argument("--gas", type=float, help="gas_level, MQ2 raw analog reading (0-1023)")
    args = parser.parse_args()

    if args.accel is not None and args.gas is not None:
        accel = {"x": args.accel[0], "y": args.accel[1], "z": args.accel[2]}
        gyro = {"x": args.gyro[0], "y": args.gyro[1], "z": args.gyro[2]} if args.gyro else None
        gas_level = args.gas
    else:
        print("No/incomplete flags given -- prompting interactively (press Enter to accept defaults).\n")
        accel = _prompt_triplet("accel", (10.0, 7.0, 5.0))
        has_gyro = input("Include gyro reading? [y/N]: ").strip().lower() == "y"
        gyro = _prompt_triplet("gyro", (70.0, -65.0, 50.0)) if has_gyro else None
        gas_level = _prompt_float("gas_level (0-1023)", 850.0)

    svc = InferenceService()

    print("\n--- Input ---")
    print(f"accel: {accel}")
    print(f"gyro:  {gyro}")
    print(f"gas_level: {gas_level}")

    print("\n--- Predictions ---")
    print("severity:", svc.predict_severity(accel=accel, gyro=gyro))
    print("anomaly: ", svc.predict_anomaly(gas_level=gas_level, accel=accel))


if __name__ == "__main__":
    main()
