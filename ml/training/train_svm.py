"""Trains the SVM severity classifier on the synthetic sensor dataset.

Usage: python training/train_svm.py
Reads:  ml/data/synthetic_sensor_data.csv
Writes: ml/models/svm_severity.joblib, updates ml/models/model_metadata.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

sys.path.append(str(Path(__file__).resolve().parent))
from features import SVM_FEATURE_ORDER, accel_axis_std, accel_magnitude, gyro_magnitude, jerk

RANDOM_SEED = 42
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "synthetic_sensor_data.csv"
MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "svm_severity.joblib"
METADATA_PATH = Path(__file__).resolve().parent.parent / "models" / "model_metadata.json"
CLASS_LABELS = ["minor", "moderate", "severe"]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    feats = pd.DataFrame(index=df.index)
    feats["accel_magnitude"] = df.apply(lambda r: accel_magnitude(r.accel_x, r.accel_y, r.accel_z), axis=1)
    feats["accel_axis_std"] = df.apply(lambda r: accel_axis_std(r.accel_x, r.accel_y, r.accel_z), axis=1)
    feats["gyro_magnitude"] = df.apply(lambda r: gyro_magnitude(r.gyro_x, r.gyro_y, r.gyro_z), axis=1)
    feats["jerk"] = df.apply(
        lambda r: jerk(feats.loc[r.name, "accel_magnitude"], r.prev_accel_magnitude), axis=1
    )
    return feats[SVM_FEATURE_ORDER]


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
    X = build_features(df)
    y = df["severity"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train.to_numpy())
    X_test_scaled = scaler.transform(X_test.to_numpy())

    clf = SVC(kernel="rbf", C=1.0, gamma="scale", probability=True, random_state=RANDOM_SEED)
    clf.fit(X_train_scaled, y_train)

    y_pred = clf.predict(X_test_scaled)
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)
    cm = confusion_matrix(y_test, y_pred, labels=CLASS_LABELS)

    print(f"Accuracy: {acc:.4f}")
    print(classification_report(y_test, y_pred))
    print("Confusion matrix (rows=true, cols=pred), order:", CLASS_LABELS)
    print(cm)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": clf, "scaler": scaler}, MODEL_PATH)
    print(f"Saved model to {MODEL_PATH}")

    _save_metadata(
        {
            "svm": {
                "feature_order": SVM_FEATURE_ORDER,
                "class_labels": CLASS_LABELS,
                "test_accuracy": acc,
                "classification_report": report,
                "confusion_matrix": cm.tolist(),
                "random_state": RANDOM_SEED,
                "kernel": "rbf",
            }
        }
    )


if __name__ == "__main__":
    main()
