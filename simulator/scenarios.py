"""
Scenario generators for the sensor simulator.

Each scenario is a small stateful generator class implementing
`next_reading(tick: int) -> SensorSample`. The main script
(sensor_simulator.py) just asks for the next sample on each publish tick
and doesn't need to know the internals of any given scenario.

Values here are deliberately generic/realistic ranges, not tuned to any
specific trained model's decision boundary — the ML models in `ml/`
(Sprint S3) decide what counts as "severe" vs "moderate" vs "normal" from
these readings. If the trained SVM/GMM don't fire on these scenarios,
adjust the magnitudes below (see README.md) rather than assuming the
simulator or backend is broken.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass
class SensorSample:
    accel: tuple[float, float, float]
    gyro: tuple[float, float, float]
    gas_level: float
    lat: float
    lng: float


GRAVITY_Z = 9.81

# Starting point: Mangaluru, Karnataka (arbitrary realistic default location)
DEFAULT_START_LAT = 12.9141
DEFAULT_START_LNG = 74.8560


class BaseScenario:
    """Shared state: a slowly-drifting GPS track and a gas baseline."""

    name = "base"

    def __init__(self, start_lat: float = DEFAULT_START_LAT, start_lng: float = DEFAULT_START_LNG) -> None:
        self.lat = start_lat
        self.lng = start_lng
        self.gas_baseline = random.uniform(80.0, 130.0)
        # Small constant heading so GPS drifts in a consistent direction,
        # like a vehicle actually driving somewhere (not a random walk).
        self._heading_lat = random.uniform(-1, 1) * 0.00003
        self._heading_lng = random.uniform(-1, 1) * 0.00003

    def _drift_gps(self) -> None:
        self.lat += self._heading_lat + random.uniform(-0.000005, 0.000005)
        self.lng += self._heading_lng + random.uniform(-0.000005, 0.000005)

    def _normal_accel(self) -> tuple[float, float, float]:
        return (
            random.gauss(0.0, 0.08),
            random.gauss(0.0, 0.08),
            random.gauss(GRAVITY_Z, 0.05),
        )

    def _normal_gyro(self) -> tuple[float, float, float]:
        return (
            random.gauss(0.0, 0.5),
            random.gauss(0.0, 0.5),
            random.gauss(0.0, 0.5),
        )

    def _normal_gas(self) -> float:
        return max(0.0, self.gas_baseline + random.gauss(0.0, 4.0))

    def next_reading(self, tick: int) -> SensorSample:
        raise NotImplementedError


class NormalScenario(BaseScenario):
    """Everything is fine: gentle noise around a stable baseline."""

    name = "normal"

    def next_reading(self, tick: int) -> SensorSample:
        self._drift_gps()
        return SensorSample(
            accel=self._normal_accel(),
            gyro=self._normal_gyro(),
            gas_level=self._normal_gas(),
            lat=self.lat,
            lng=self.lng,
        )


class _ImpactScenario(BaseScenario):
    """
    Shared logic for crash-like scenarios: normal driving, then a sharp
    accel + gyro spike lasting a few ticks, then a post-impact "stopped"
    period (near-zero motion, engine presumably off).
    """

    name = "impact"
    spike_start_tick = 10
    spike_duration_ticks = 4
    accel_spike_magnitude = 30.0  # m/s^2, added on top of gravity
    gyro_spike_magnitude = 250.0  # deg/s

    def next_reading(self, tick: int) -> SensorSample:
        self._drift_gps()

        in_spike = self.spike_start_tick <= tick < self.spike_start_tick + self.spike_duration_ticks
        after_spike = tick >= self.spike_start_tick + self.spike_duration_ticks

        if in_spike:
            accel = (
                random.uniform(-1, 1) * self.accel_spike_magnitude,
                random.uniform(-1, 1) * self.accel_spike_magnitude,
                GRAVITY_Z + random.uniform(-1, 1) * self.accel_spike_magnitude,
            )
            gyro = (
                random.uniform(-1, 1) * self.gyro_spike_magnitude,
                random.uniform(-1, 1) * self.gyro_spike_magnitude,
                random.uniform(-1, 1) * self.gyro_spike_magnitude,
            )
        elif after_spike:
            # Vehicle stopped: near-zero lateral motion, gravity only.
            accel = (random.gauss(0.0, 0.05), random.gauss(0.0, 0.05), random.gauss(GRAVITY_Z, 0.05))
            gyro = (random.gauss(0.0, 0.1), random.gauss(0.0, 0.1), random.gauss(0.0, 0.1))
        else:
            accel = self._normal_accel()
            gyro = self._normal_gyro()

        return SensorSample(
            accel=accel,
            gyro=gyro,
            gas_level=self._normal_gas(),
            lat=self.lat,
            lng=self.lng,
        )


class SevereCrashScenario(_ImpactScenario):
    name = "severe_crash"
    accel_spike_magnitude = 45.0
    gyro_spike_magnitude = 350.0
    spike_duration_ticks = 5


class ModerateImpactScenario(_ImpactScenario):
    name = "moderate_impact"
    accel_spike_magnitude = 18.0
    gyro_spike_magnitude = 120.0
    spike_duration_ticks = 3


class GasLeakScenario(BaseScenario):
    """
    Gas level ramps up steadily starting a few ticks in, then stays
    elevated (sustained anomaly, not a single spike) — matches
    MQTT_SPEC.md's framing of gas_leak as something the GMM anomaly
    detector should catch over multiple readings, not a one-off blip.
    """

    name = "gas_leak"
    ramp_start_tick = 8
    ramp_duration_ticks = 10
    peak_gas_level = 700.0

    def next_reading(self, tick: int) -> SensorSample:
        self._drift_gps()

        if tick < self.ramp_start_tick:
            gas = self._normal_gas()
        elif tick < self.ramp_start_tick + self.ramp_duration_ticks:
            progress = (tick - self.ramp_start_tick) / self.ramp_duration_ticks
            gas = self.gas_baseline + progress * (self.peak_gas_level - self.gas_baseline)
            gas += random.gauss(0.0, 5.0)
        else:
            gas = self.peak_gas_level + random.gauss(0.0, 15.0)

        return SensorSample(
            accel=self._normal_accel(),
            gyro=self._normal_gyro(),
            gas_level=max(0.0, gas),
            lat=self.lat,
            lng=self.lng,
        )


SCENARIOS: dict[str, type[BaseScenario]] = {
    "normal": NormalScenario,
    "severe_crash": SevereCrashScenario,
    "moderate_impact": ModerateImpactScenario,
    "gas_leak": GasLeakScenario,
}


def get_scenario(name: str) -> BaseScenario:
    try:
        scenario_cls = SCENARIOS[name]
    except KeyError:
        valid = ", ".join(sorted(SCENARIOS))
        raise ValueError(f"Unknown scenario '{name}'. Valid options: {valid}") from None
    return scenario_cls()
