"""Sync trained ML models and code from repo-root ml/ into backend/app/ml/."""
import shutil
import sys
from pathlib import Path


def main() -> None:
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[3]

    ml_dir = repo_root / "ml"
    backend_ml_dir = script_path.parent
    models_dir = backend_ml_dir / "models"

    if not ml_dir.is_dir():
        print(f"Error: Source ML directory not found at {ml_dir}", file=sys.stderr)
        sys.exit(1)

    files_to_copy = [
        (ml_dir / "training" / "features.py", backend_ml_dir / "features.py"),
        (ml_dir / "inference.py", backend_ml_dir / "_inference_service.py"),
        (ml_dir / "models" / "svm_severity.joblib", models_dir / "svm_severity.joblib"),
        (ml_dir / "models" / "gmm_anomaly.joblib", models_dir / "gmm_anomaly.joblib"),
        (ml_dir / "models" / "model_metadata.json", models_dir / "model_metadata.json"),
    ]

    for src, _ in files_to_copy:
        if not src.is_file():
            print(f"Error: Missing source file {src}", file=sys.stderr)
            sys.exit(1)

    models_dir.mkdir(parents=True, exist_ok=True)

    print("Copying ML model artifacts and modules...")
    for src, dst in files_to_copy:
        shutil.copy2(src, dst)
        print(f"  {src.relative_to(repo_root)} -> {dst.relative_to(repo_root)}")

    print("Model sync completed successfully.")


if __name__ == "__main__":
    main()
