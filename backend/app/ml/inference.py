"""
ML inference STUB.

TODO(Sprint S3): Replace with real SVM (severity classification) and
GMM (anomaly/gas-leak detection) model loading + inference, per
PROJECT_CONSTITUTION.md non-negotiable #4 (SVM and GMM are not
interchangeable — SVM handles supervised severity, GMM handles
unsupervised anomaly detection).

For Sprint S2 this always returns a fixed placeholder result and never
creates an incident, so ingestion can be verified end-to-end without
real model logic. Sprint S3 wires this into `mqtt/client.py`'s
`_maybe_flag_incident` hook.
"""
from dataclasses import dataclass


@dataclass
class InferenceResult:
    is_incident: bool
    incident_type: str | None  # "accident" | "gas_leak"
    severity: str | None
    severity_score: float | None
    anomaly_score: float | None


# Placeholder scores returned by the stub — clearly not derived from any model.
_PLACEHOLDER_SEVERITY_SCORE = 0.0
_PLACEHOLDER_ANOMALY_SCORE = 0.0


def run_inference(
    *,
    accel_x: float,
    accel_y: float,
    accel_z: float,
    gyro_x: float | None,
    gyro_y: float | None,
    gyro_z: float | None,
    gas_level: float,
) -> InferenceResult:
    """
    STUB: always returns a fixed, non-incident placeholder result.

    Sprint S3 replaces this body with:
      - SVM inference on accel/gyro features -> severity_score / severity
      - GMM inference on gas_level (+ features) -> anomaly_score
      - thresholding to decide is_incident / incident_type
    """
    return InferenceResult(
        is_incident=False,
        incident_type=None,
        severity=None,
        severity_score=_PLACEHOLDER_SEVERITY_SCORE,
        anomaly_score=_PLACEHOLDER_ANOMALY_SCORE,
    )
