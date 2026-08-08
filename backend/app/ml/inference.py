"""
ML inference — real SVM (severity classification) and GMM (anomaly/gas-leak detection) models.

Loads trained models once via `InferenceService` on module load, wrapped by `run_inference()`
which adapts the output into 0 to 2 `InferenceResult` objects (one for SVM severity if non-minor,
one for GMM anomaly if gas leak detected).
"""
from dataclasses import dataclass

from ._inference_service import InferenceService


@dataclass
class InferenceResult:
    is_incident: bool
    incident_type: str | None  # "accident" | "gas_leak"
    severity: str | None
    severity_score: float | None
    anomaly_score: float | None


_service: InferenceService | None = None


def get_inference_service() -> InferenceService:
    global _service
    if _service is None:
        _service = InferenceService()
    return _service


def run_inference(
    *,
    accel_x: float,
    accel_y: float,
    accel_z: float,
    gyro_x: float | None,
    gyro_y: float | None,
    gyro_z: float | None,
    gas_level: float,
) -> list[InferenceResult]:
    svc = get_inference_service()
    results: list[InferenceResult] = []

    accel = {"x": accel_x, "y": accel_y, "z": accel_z}
    gyro = (
        {"x": gyro_x, "y": gyro_y, "z": gyro_z}
        if gyro_x is not None and gyro_y is not None and gyro_z is not None
        else None
    )

    # SVM Severity Prediction
    sev_res = svc.predict_severity(accel=accel, gyro=gyro)
    if sev_res["severity"] in ("moderate", "severe"):
        results.append(
            InferenceResult(
                is_incident=True,
                incident_type="accident",
                severity=sev_res["severity"],
                severity_score=sev_res["score"],
                anomaly_score=None,
            )
        )

    # GMM Anomaly Prediction
    anom_res = svc.predict_anomaly(gas_level=gas_level, accel=accel)
    if anom_res["is_anomaly"]:
        results.append(
            InferenceResult(
                is_incident=True,
                incident_type="gas_leak",
                severity=None,
                severity_score=None,
                anomaly_score=anom_res["score"],
            )
        )

    return results
