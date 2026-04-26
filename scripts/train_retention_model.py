"""
One-time training script for the RetentionCurvePredictor.

Usage:
    python scripts/train_retention_model.py

Steps:
    1. Builds retention_dataset.json if it doesn't exist
    2. Trains the RetentionCurvePredictor
    3. Prints train/val MAE per timepoint
    4. Saves model to viral_script_engine/retention/model.joblib
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from viral_script_engine.retention.training_data.build_dataset import build, _OUTPUT_PATH
from viral_script_engine.retention.curve_predictor import RetentionCurvePredictor

_CULTURAL_KB_PATH = str(
    Path(__file__).parent.parent / "viral_script_engine" / "data" / "cultural_kb.json"
)


def main():
    # Step 1: build dataset if missing
    if not _OUTPUT_PATH.exists():
        print("Building retention dataset...")
        out = build()
        print(f"  Dataset created: {out}")
    else:
        print(f"Dataset already exists: {_OUTPUT_PATH}")

    # Step 2: train the predictor
    print("\nTraining RetentionCurvePredictor...")
    predictor = RetentionCurvePredictor()
    result = predictor.train(
        dataset_path=str(_OUTPUT_PATH),
        cultural_kb_path=_CULTURAL_KB_PATH,
    )

    avg_mae = result["avg_mae"]
    print(f"\nRetention model trained. Avg MAE: {avg_mae:.4f}. Model saved.")


if __name__ == "__main__":
    main()
