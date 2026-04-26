import json
from pathlib import Path
from typing import List, Optional

import numpy as np
from pydantic import BaseModel
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor
import joblib

from viral_script_engine.retention.feature_extractor import FeatureExtractor, ScriptFeatures

_MODEL_PATH = Path(__file__).parent / "model.joblib"

CURVE_TIMEPOINTS = [0, 3, 6, 10, 15, 20, 25, 30, 45, 60]


class RetentionCurve(BaseModel):
    timepoints: List[int]
    values: List[float]
    area_under_curve: float
    drop_off_point: int  # first timepoint where retention drops below 0.5

    @classmethod
    def from_values(cls, values: List[float]) -> "RetentionCurve":
        tps = CURVE_TIMEPOINTS
        # Trapezoidal AUC, normalised to [0, 1]
        auc = 0.0
        for i in range(len(tps) - 1):
            dt = tps[i + 1] - tps[i]
            auc += dt * (values[i] + values[i + 1]) / 2
        total_duration = tps[-1] - tps[0]
        auc = auc / total_duration if total_duration > 0 else 0.0

        drop_off = tps[-1]
        for t, v in zip(tps, values):
            if v < 0.5:
                drop_off = t
                break

        return cls(
            timepoints=list(tps),
            values=[round(v, 4) for v in values],
            area_under_curve=round(auc, 4),
            drop_off_point=drop_off,
        )


class RetentionCurvePredictor:
    """
    Predicts a 10-point retention curve from script features.
    10 points = retention at seconds [0, 3, 6, 10, 15, 20, 25, 30, 45, 60].

    Uses MultiOutputRegressor(GradientBoostingRegressor).
    Lightweight enough to run on CPU without GPU (<1ms per call after training).
    """

    MODEL_PATH = _MODEL_PATH
    CURVE_TIMEPOINTS = CURVE_TIMEPOINTS

    def __init__(self):
        if _MODEL_PATH.exists():
            self.model = joblib.load(_MODEL_PATH)
            self._trained = True
        else:
            self.model = MultiOutputRegressor(
                GradientBoostingRegressor(n_estimators=100, max_depth=4, random_state=42)
            )
            self._trained = False

    def train(
        self,
        dataset_path: Optional[str] = None,
        cultural_kb_path: Optional[str] = None,
    ) -> dict:
        """
        Train on retention_dataset.json. Saves model to MODEL_PATH.
        Returns dict with avg_mae and mae_per_timepoint.
        """
        if dataset_path is None:
            dataset_path = str(
                Path(__file__).parent / "training_data" / "retention_dataset.json"
            )

        with open(dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        extractor = FeatureExtractor(cultural_kb_path=cultural_kb_path)

        X: List[List[float]] = []
        y: List[List[float]] = []
        skipped = 0
        for sample in data["samples"]:
            try:
                features = extractor.extract(
                    sample["script_text"], sample["platform"], sample["region"]
                )
                vec = features.to_vector()
                if any(v != v for v in vec):  # NaN check
                    skipped += 1
                    continue
                X.append(vec)
                y.append(sample["retention_curve"])
            except Exception:
                skipped += 1

        if not X:
            raise RuntimeError("No valid training samples extracted.")

        X_arr = np.array(X, dtype=float)
        y_arr = np.array(y, dtype=float)

        n = len(X_arr)
        rng = np.random.RandomState(42)
        idx = rng.permutation(n)
        split = max(1, int(n * 0.8))
        X_train, X_val = X_arr[idx[:split]], X_arr[idx[split:]]
        y_train, y_val = y_arr[idx[:split]], y_arr[idx[split:]]

        self.model.fit(X_train, y_train)
        self._trained = True

        val_preds = np.clip(self.model.predict(X_val), 0.0, 1.0)
        mae_per_tp = np.mean(np.abs(val_preds - y_val), axis=0).tolist()
        avg_mae = float(np.mean(mae_per_tp))

        print(f"  Trained on {len(X_train)} samples, validated on {len(X_val)} (skipped {skipped})")
        print("  Train/Val MAE per timepoint:")
        for t, mae in zip(CURVE_TIMEPOINTS, mae_per_tp):
            print(f"    {t:2d}s: {mae:.4f}")
        print(f"  Avg MAE: {avg_mae:.4f}")

        joblib.dump(self.model, _MODEL_PATH)
        print(f"  Model saved to {_MODEL_PATH}")

        return {"avg_mae": avg_mae, "mae_per_timepoint": mae_per_tp}

    def predict(self, features: ScriptFeatures) -> RetentionCurve:
        if not self._trained:
            raise RuntimeError("Model not trained. Run train() first.")
        vec = np.array(features.to_vector(), dtype=float).reshape(1, -1)
        raw = self.model.predict(vec)[0]
        clipped = np.clip(raw, 0.0, 1.0)
        values = self._enforce_monotonic_decrease(clipped).tolist()
        return RetentionCurve.from_values(values)

    @staticmethod
    def _enforce_monotonic_decrease(values: np.ndarray) -> np.ndarray:
        result = values.copy()
        for i in range(1, len(result)):
            result[i] = min(result[i], result[i - 1])
        return result
