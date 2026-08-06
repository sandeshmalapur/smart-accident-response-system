"""Generates synthetic sensor data matching the sensor_readings schema
(DATABASE_SCHEMA.md) and MQTT telemetry payload shape (MQTT_SPEC.md),
labeled with severity class (SVM target) and a gas-anomaly flag (GMM target).

No real sensor dataset exists yet for this project -- this script is the
stand-in data source until real IoT data is available.

Column naming matches sensor_readings exactly (accel_x/y/z, gyro_x/y/z,
gas_level, latitude, longitude) so this CSV could be swapped for a real
export from that table without renaming anything downstream.
`prev_accel_magnitude` is a synthetic-only convenience column (not a real
sensor_readings column) -- it lets train_svm.py compute jerk without needing
true time-series rows; the real backend derives it at inference time from
the previous reading in a device's stream.

Usage: python training/generate_synthetic_data.py [--rows-per-class N] [--seed N]
"""
from __future__ import annotations

import argparse
import csv
import random
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

RANDOM_SEED = 42
SEVERITY_CLASSES = ["minor", "moderate", "severe"]
ROWS_PER_CLASS_DEFAULT = 2000
GAS_ANOMALY_RATE = 0.08  # fraction of rows with an elevated/anomalous gas reading


@dataclass
class SyntheticRow:
    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float
    gyro_y: float
    gyro_z: float
    gas_level: float
    latitude: float
    longitude: float
    prev_accel_magnitude: float
    severity: str
    gas_anomaly: int


def _gps_near(base_lat: float = 12.9141, base_lng: float = 74.8560, jitter: float = 0.01) -> tuple[float, float]:
    # Jittered placeholder coordinates -- GPS is not a model feature, just
    # needed to keep the row shape consistent with sensor_readings.
    return base_lat + random.uniform(-jitter, jitter), base_lng + random.uniform(-jitter, jitter)


def _gen_minor(rng: np.random.Generator) -> SyntheticRow:
    # Normal driving: low, stable accel; gyro near zero; gas normal
    # (MQ2 raw analog reading, mid-low end of the 0-1023 simulated range).
    ax, ay, az = rng.normal(0, 0.4, 3)
    gx, gy, gz = rng.normal(0, 3, 3)
    prev_mag = float(np.linalg.norm([ax, ay, az]) + rng.normal(0, 0.1))
    gas = float(np.clip(rng.normal(200, 60), 0, 1023))
    lat, lng = _gps_near()
    return SyntheticRow(ax, ay, az, gx, gy, gz, gas, lat, lng, max(prev_mag, 0.0), "minor", 0)


def _gen_moderate(rng: np.random.Generator) -> SyntheticRow:
    # Moderate impact: a noticeable accel spike on 1-2 axes, mild gyro shift.
    ax = rng.normal(4.0, 1.2)
    ay = rng.normal(1.0, 0.8)
    az = rng.normal(0.5, 0.5)
    gx, gy, gz = rng.normal(0, 15, 3)
    prev_mag = float(np.linalg.norm([ax, ay, az]) * rng.uniform(0.3, 0.6))
    gas = float(np.clip(rng.normal(210, 70), 0, 1023))
    lat, lng = _gps_near()
    return SyntheticRow(ax, ay, az, gx, gy, gz, gas, lat, lng, max(prev_mag, 0.0), "moderate", 0)


def _gen_severe(rng: np.random.Generator) -> SyntheticRow:
    # Severe impact: large multi-axis accel spike, possible rollover -> large gyro.
    ax = rng.normal(9.0, 2.0)
    ay = rng.normal(6.0, 2.0)
    az = rng.normal(4.0, 1.5)
    gx, gy, gz = rng.normal(0, 60, 3)
    prev_mag = float(np.linalg.norm([ax, ay, az]) * rng.uniform(0.05, 0.25))
    gas = float(np.clip(rng.normal(210, 70), 0, 1023))
    lat, lng = _gps_near()
    return SyntheticRow(ax, ay, az, gx, gy, gz, gas, lat, lng, max(prev_mag, 0.0), "severe", 0)


def generate(rows_per_class: int, seed: int = RANDOM_SEED) -> list[SyntheticRow]:
    random.seed(seed)
    rng = np.random.default_rng(seed)
    generators = {"minor": _gen_minor, "moderate": _gen_moderate, "severe": _gen_severe}

    rows: list[SyntheticRow] = []
    for _label, gen_fn in generators.items():
        for _ in range(rows_per_class):
            rows.append(gen_fn(rng))

    # Overlay gas anomalies independently of severity class -- a gas leak
    # (GMM target) is a separate phenomenon from an impact event.
    n_anomalous = int(len(rows) * GAS_ANOMALY_RATE)
    anomaly_indices = rng.choice(len(rows), size=n_anomalous, replace=False)
    for idx in anomaly_indices:
        row = rows[idx]
        row.gas_level = float(np.clip(rng.normal(750, 130), 400, 1023))
        row.gas_anomaly = 1

    random.shuffle(rows)
    return rows


def write_csv(rows: list[SyntheticRow], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows-per-class", type=int, default=ROWS_PER_CLASS_DEFAULT)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "synthetic_sensor_data.csv",
    )
    args = parser.parse_args()

    rows = generate(args.rows_per_class, args.seed)
    write_csv(rows, args.out)

    counts = {c: sum(1 for r in rows if r.severity == c) for c in SEVERITY_CLASSES}
    n_anomaly = sum(r.gas_anomaly for r in rows)
    print(f"Wrote {len(rows)} rows to {args.out}")
    print(f"Severity class balance: {counts}")
    print(f"Gas anomaly rows: {n_anomaly} ({n_anomaly / len(rows):.1%})")


if __name__ == "__main__":
    main()
