from typing import Optional

from pydantic import BaseModel

from viral_script_engine.retention.curve_predictor import RetentionCurve, RetentionCurvePredictor
from viral_script_engine.retention.curve_scorer import CurveScorerResult, RetentionCurveScorer
from viral_script_engine.retention.feature_extractor import FeatureExtractor


class RetentionRewardResult(BaseModel):
    score: float
    original_curve: RetentionCurve
    new_curve: RetentionCurve
    curve_delta: CurveScorerResult


class RetentionCurveReward:
    """
    Wraps the full retention prediction + scoring pipeline into a reward signal.

    Caches the original curve per episode so the extractor is called only once
    for the original script — subsequent steps reuse the cached curve.
    """

    def __init__(self, cultural_kb_path: Optional[str] = None):
        self.extractor = FeatureExtractor(cultural_kb_path=cultural_kb_path)
        self.predictor = RetentionCurvePredictor()
        self.scorer = RetentionCurveScorer()
        self._original_curve_cache: dict = {}

    def score(
        self,
        original_script: str,
        rewritten_script: str,
        platform: str,
        region: str,
        action_type: str,
        episode_id: str,
    ) -> RetentionRewardResult:
        # Cache original curve — compute only once per episode
        if episode_id not in self._original_curve_cache:
            orig_features = self.extractor.extract(original_script, platform, region)
            self._original_curve_cache[episode_id] = self.predictor.predict(orig_features)

        new_features = self.extractor.extract(rewritten_script, platform, region)
        new_curve = self.predictor.predict(new_features)

        result = self.scorer.score(
            original_curve=self._original_curve_cache[episode_id],
            new_curve=new_curve,
            action_type=action_type,
        )

        return RetentionRewardResult(
            score=result.final_score,
            original_curve=self._original_curve_cache[episode_id],
            new_curve=new_curve,
            curve_delta=result,
        )

    def clear_cache(self, episode_id: Optional[str] = None) -> None:
        if episode_id:
            self._original_curve_cache.pop(episode_id, None)
        else:
            self._original_curve_cache.clear()
