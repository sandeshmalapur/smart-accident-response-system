"""Unit tests for InferenceService.

Run with: pytest ml/tests/test_inference.py
Requires trained model artifacts to exist (run the training scripts first).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent))
from inference import InferenceService

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


@pytest.fixture(scope="module")
def service() -> InferenceService:
    if not (MODELS_DIR / "svm_severity.joblib").exists() or not (MODELS_DIR / "gmm_anomaly.joblib").exists():
        pytest.skip("Trained model artifacts not found -- run training scripts first")
    return InferenceService()


def test_severe_pattern_returns_severe_class(service: InferenceService) -> None:
    result = service.predict_severity(
        accel={"x": 10.0, "y": 7.0, "z": 5.0},
        gyro={"x": 70, "y": -65, "z": 50},
    )
    assert result["severity"] == "severe"
    assert 0.0 <= result["score"] <= 1.0


def test_high_gas_level_flagged_as_anomaly(service: InferenceService) -> None:
    result = service.predict_anomaly(gas_level=850.0)
    assert result["is_anomaly"] is True
