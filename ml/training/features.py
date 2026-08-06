"""Shared feature engineering for the Smart Accident Response System ML models.

Raw sensor reading shape (per MQTT_SPEC.md telemetry payload / sensor_readings
table):
    accel: {x, y, z}   -- m/s^2 (accel_x/y/z, NOT NULL)
    gyro:  {x, y, z}   -- deg/s (gyro_x/y/z, nullable -- device may not report it)
    gas_level: float   -- MQ2-equivalent raw analog reading, 0-1023 simulated
                          range (gas_level, NOT NULL)
    latitude, longitude: float -- not used as a model feature (location, not signal)

All feature functions are pure and dependency-light (numpy only) so this
module can be imported unchanged inside backend/app/ml/inference.py later.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np

# MQ2 sensor's simulated raw analog range per MQTT_SPEC.md ("0-1023 simulated
# range"). Pulled out as a named constant per the "no hardcoded magic
# numbers" rule -- adjust here if the real MQ2 hardware calibration differs.
GAS_LEVEL_MAX = 1023.0

SVM_FEATURE_ORDER = ["accel_magnitude", "accel_axis_std", "gyro_magnitude", "jerk"]
GMM_FEATURE_ORDER = ["gas_level_norm", "accel_magnitude"]


def accel_magnitude(x: float, y: float, z: float) -> float:
    return math.sqrt(x ** 2 + y ** 2 + z ** 2)


def accel_axis_std(x: float, y: float, z: float) -> float:
    """Spread across the three axes -- helps distinguish a single-axis hard
    brake from a multi-axis rollover-style impact."""
    return float(np.std([x, y, z]))


def gyro_magnitude(x: Optional[float], y: Optional[float], z: Optional[float]) -> float:
    if x is None or y is None or z is None:
        return 0.0
    return math.sqrt(x ** 2 + y ** 2 + z ** 2)


def jerk(accel_mag: float, prev_accel_mag: Optional[float], dt: float = 1.0) -> float:
    """Rate of change of acceleration magnitude between consecutive readings.
    prev_accel_mag=None (first reading in a stream) -> jerk defaults to 0.
    """
    if prev_accel_mag is None or dt <= 0:
        return 0.0
    return (accel_mag - prev_accel_mag) / dt


def normalize_gas_level(gas_level: float) -> float:
    return float(np.clip(gas_level / GAS_LEVEL_MAX, 0.0, 1.0))


def build_svm_features(
    accel: dict, gyro: Optional[dict], prev_accel_magnitude: Optional[float] = None
) -> list[float]:
    a_mag = accel_magnitude(accel["x"], accel["y"], accel["z"])
    a_std = accel_axis_std(accel["x"], accel["y"], accel["z"])
    g_mag = gyro_magnitude(
        gyro.get("x") if gyro else None,
        gyro.get("y") if gyro else None,
        gyro.get("z") if gyro else None,
    )
    j = jerk(a_mag, prev_accel_magnitude)
    return [a_mag, a_std, g_mag, j]


def build_gmm_features(gas_level: float, accel: dict) -> list[float]:
    g_norm = normalize_gas_level(gas_level)
    a_mag = accel_magnitude(accel["x"], accel["y"], accel["z"])
    return [g_norm, a_mag]
