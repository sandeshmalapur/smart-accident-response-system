"""Dependency-light inference wrapper for the trained severity (SVM) and
anomaly (GMM) models.

This module has no FastAPI/DB imports so it can be copied as-is into
backend/app/ml/inference.py when Backend Sprint S2 wires it in. It depends
only on: sklearn (via joblib-loaded artifacts), joblib, numpy, and this
package's own features.py (which must travel with it).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, TypedDict

import joblib
import numpy as np

try:
    from training.features import build_gmm_features, build_svm_features
except ImportError:  # allows running from within backend/app/ml/ once dropped in
    from features import build_gmm_features, build_svm_features  # type: ignore

MODELS_DIR = Path(__file__).resolve().parent / "models"
SVM_MODEL_PATH = MODELS_DIR / "svm_severity.joblib"
GMM_MODEL_PATH = MODELS_DIR / "gmm_anomaly.joblib"
METADATA_PATH = MODELS_DIR / "model_metadata.json"


class SeverityResult(TypedDict):
    severity: str
    score: float


class AnomalyResult(TypedDict):
    is_anomaly: bool
    score: float


class InferenceService:
    """Loads both trained models once and exposes prediction methods.

    Usage:
        svc = InferenceService()
        svc.predict_severity(accel={"x": 8.1, "y": 5.9, "z": 3.2}, gyro={"x": 40, "y": -55, "z": 12})
        svc.predict_anomaly(gas_level=720.0)
    """

    def __init__(
        self,
        svm_path: Path = SVM_MODEL_PATH,
        gmm_path: Path = GMM_MODEL_PATH,
        metadata_path: Path = METADATA_PATH,
    ) -> None:
        svm_bundle = joblib.load(svm_path)
        self._svm_model = svm_bundle["model"]
        self._svm_scaler = svm_bundle["scaler"]

        gmm_bundle = joblib.load(gmm_path)
        self._gmm_model = gmm_bundle["model"]
        self._gmm_scaler = gmm_bundle["scaler"]
        self._gmm_threshold: float = gmm_bundle["threshold"]

        self._metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}

    def predict_severity(
        self,
        accel: dict,
        gyro: Optional[dict] = None,
        prev_accel_magnitude: Optional[float] = None,
    ) -> SeverityResult:
        """accel/gyro: {"x": float, "y": float, "z": float}. gyro may be None
        if the device doesn't report it. prev_accel_magnitude enables the
        jerk feature when the caller is tracking a reading stream; omit for
        a single one-off reading (jerk defaults to 0)."""
        features = np.array([build_svm_features(accel, gyro, prev_accel_magnitude)])
        features_scaled = self._svm_scaler.transform(features)
        pred_class = self._svm_model.predict(features_scaled)[0]
        probs = self._svm_model.predict_proba(features_scaled)[0]
        class_index = list(self._svm_model.classes_).index(pred_class)
        score = float(probs[class_index])
        return {"severity": str(pred_class), "score": round(score, 4)}

    def predict_anomaly(self, gas_level: float, accel: Optional[dict] = None) -> AnomalyResult:
        """accel is optional (defaults to a zero vector) since the GMM was
        fit jointly on gas_level + accel_magnitude -- pass the concurrent
        accel reading when available for a more accurate score."""
        accel = accel or {"x": 0.0, "y": 0.0, "z": 0.0}
        features = np.array([build_gmm_features(gas_level, accel)])
        features_scaled = self._gmm_scaler.transform(features)
        score = float(self._gmm_model.score_samples(features_scaled)[0])
        is_anomaly = score < self._gmm_threshold
        return {"is_anomaly": bool(is_anomaly), "score": round(score, 4)}
