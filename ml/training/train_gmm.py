"""Trains the GMM anomaly detector on normal gas_level + accel distributions.

Fits on gas_anomaly == 0 rows only (i.e. "normal" operating conditions), then
picks a log-likelihood threshold from a low percentile of the normal
distribution's own scores -- so a small, known fraction of even normal data
sits below threshold. That fraction is recorded in metadata as the
justification for the chosen threshold.

Usage: python training/train_gmm.py
Reads:  ml/data/synthetic_sensor_data.csv
Writes: ml/models/gmm_anomaly.joblib, updates ml/models/model_metadata.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

sys.path.append(str(Path(__file__).resolve().parent))
from features import GMM_FEATURE_ORDER, accel_magnitude, normalize_gas_level

RANDOM_SEED = 42
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "synthetic_sensor_data.csv"
MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "gmm_anomaly.joblib"
METADATA_PATH = Path(__file__).resolve().parent.parent / "models" / "model_metadata.json"

# Threshold picked at the Nth percentile of NORMAL data's own log-likelihood
# scores -- i.e. we accept flagging this fraction of normal rows as false
# positives in exchange for catching genuine anomalies below it.
THRESHOLD_PERCENTILE = 2.0
N_COMPONENTS = 2


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    feats = pd.DataFrame(index=df.index)
    feats["gas_level_norm"] = df["gas_level"].apply(normalize_gas_level)
    feats["accel_magnitude"] = df.apply(lambda r: accel_magnitude(r.accel_x, r.accel_y, r.accel_z), axis=1)
    return feats[GMM_FEATURE_ORDER]


def _load_metadata() -> dict:
    if METADATA_PATH.exists():
        return json.loads(METADATA_PATH.read_text())
    return {}


def _save_metadata(update: dict) -> None:
    meta = _load_metadata()
    meta.update(update)
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    METADATA_PATH.write_text(json.dumps(meta, indent=2))


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"{DATA_PATH} not found -- run generate_synthetic_data.py first")

    df = pd.read_csv(DATA_PATH)
    X_all = build_features(df)
    normal_mask = df["gas_anomaly"] == 0

    scaler = StandardScaler()
    X_normal_scaled = scaler.fit_transform(X_all[normal_mask].to_numpy())

    gmm = GaussianMixture(n_components=N_COMPONENTS, covariance_type="full", random_state=RANDOM_SEED)
    gmm.fit(X_normal_scaled)

    normal_scores = gmm.score_samples(X_normal_scaled)
    threshold = float(np.percentile(normal_scores, THRESHOLD_PERCENTILE))

    X_all_scaled = scaler.transform(X_all.to_numpy())
    all_scores = gmm.score_samples(X_all_scaled)
    predicted_anomaly = (all_scores < threshold).astype(int)

    precision = precision_score(df["gas_anomaly"], predicted_anomaly, zero_division=0)
    recall = recall_score(df["gas_anomaly"], predicted_anomaly, zero_division=0)

    print(f"Chosen threshold (log-likelihood): {threshold:.4f}")
    print(f"Justification: {THRESHOLD_PERCENTILE}th percentile of normal-only training scores")
    print(f"On full dataset -- precision: {precision:.4f}, recall: {recall:.4f}")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": gmm, "scaler": scaler, "threshold": threshold}, MODEL_PATH)
    print(f"Saved model to {MODEL_PATH}")

    _save_metadata(
        {
            "gmm": {
                "feature_order": GMM_FEATURE_ORDER,
                "threshold": threshold,
                "threshold_percentile": THRESHOLD_PERCENTILE,
                "n_components": N_COMPONENTS,
                "precision_on_full_data": precision,
                "recall_on_full_data": recall,
                "random_state": RANDOM_SEED,
            }
        }
    )


if __name__ == "__main__":
    main()
