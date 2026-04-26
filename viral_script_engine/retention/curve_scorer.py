from typing import List

from pydantic import BaseModel

from viral_script_engine.retention.curve_predictor import CURVE_TIMEPOINTS, RetentionCurve

_TP_INDEX = {t: i for i, t in enumerate(CURVE_TIMEPOINTS)}


class CurveScorerResult(BaseModel):
    final_score: float
    overall_improvement: float
    targeted_improvement: float
    regression_penalty: float
    improved_timepoints: List[int]
    worsened_timepoints: List[int]


class RetentionCurveScorer:
    """
    Scores improvement between two retention curves.

    Rewards targeted improvements at action-relevant timepoints:
      - hook_rewrite      → early timepoints (0–6s)
      - section_reorder   → mid timepoints (10–20s)
      - cultural_ref_sub  → mid-to-late (15–30s)
      - cta_placement     → late timepoints (45–60s)

    Formula:
      final = 0.50 * overall_improvement
            + 0.35 * targeted_improvement
            - 0.15 * regression_penalty
      clipped to [0, 1]
    """

    ACTION_CURVE_MAP = {
        "hook_rewrite":     [0, 3, 6],
        "section_reorder":  [10, 15, 20],
        "cultural_ref_sub": [15, 20, 25, 30],
        "cta_placement":    [45, 60],
    }

    def score(
        self,
        original_curve: RetentionCurve,
        new_curve: RetentionCurve,
        action_type: str,
    ) -> CurveScorerResult:
        orig_auc = original_curve.area_under_curve
        new_auc = new_curve.area_under_curve

        # 1. Overall AUC improvement (relative)
        if orig_auc > 0:
            overall_improvement = (new_auc - orig_auc) / orig_auc
        else:
            overall_improvement = float(new_auc)
        overall_improvement = max(-1.0, min(1.0, overall_improvement))

        # 2. Targeted improvement at action-relevant timepoints
        target_tps = self.ACTION_CURVE_MAP.get(str(action_type), CURVE_TIMEPOINTS)
        targeted_deltas: List[float] = []
        for tp in target_tps:
            i = _TP_INDEX.get(tp)
            if i is not None and i < len(original_curve.values) and i < len(new_curve.values):
                targeted_deltas.append(new_curve.values[i] - original_curve.values[i])

        if targeted_deltas:
            targeted_improvement = float(sum(targeted_deltas) / len(targeted_deltas))
        else:
            targeted_improvement = 0.0
        targeted_improvement = max(-1.0, min(1.0, targeted_improvement))

        # 3. Regression penalty: any timepoint that degraded
        improved: List[int] = []
        worsened: List[int] = []
        worsened_magnitudes: List[float] = []

        for tp, i in _TP_INDEX.items():
            if i >= len(original_curve.values) or i >= len(new_curve.values):
                continue
            delta = new_curve.values[i] - original_curve.values[i]
            if delta > 0.001:
                improved.append(tp)
            elif delta < -0.001:
                worsened.append(tp)
                worsened_magnitudes.append(abs(delta))

        regression_penalty = 0.0
        if worsened_magnitudes:
            regression_penalty = min(1.0, sum(worsened_magnitudes) / len(CURVE_TIMEPOINTS))

        final_score = (
            0.50 * max(0.0, overall_improvement)
            + 0.35 * max(0.0, targeted_improvement)
            - 0.15 * regression_penalty
        )
        final_score = max(0.0, min(1.0, final_score))

        return CurveScorerResult(
            final_score=round(final_score, 4),
            overall_improvement=round(overall_improvement, 4),
            targeted_improvement=round(targeted_improvement, 4),
            regression_penalty=round(regression_penalty, 4),
            improved_timepoints=improved,
            worsened_timepoints=worsened,
        )
