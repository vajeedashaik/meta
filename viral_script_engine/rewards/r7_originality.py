from pydantic import BaseModel

from viral_script_engine.agents.originality_agent import OriginalityOutput


class OriginalityRewardResult(BaseModel):
    score: float
    originality_score: float
    flag_count: int
    breakdown: str


class OriginalityReward:
    """
    Converts OriginalityOutput into a reward signal.

    Scoring maps directly from originality_score:
    - originality_score >= 0.8:  reward = 1.0  (genuinely distinctive)
    - originality_score 0.6–0.8: reward = originality_score
    - originality_score 0.4–0.6: reward = 0.3  (mediocre — generic but not terrible)
    - originality_score < 0.4:   reward = 0.0  (template clone — cliff penalty)
    """

    def score(self, originality_output: OriginalityOutput) -> OriginalityRewardResult:
        os_ = originality_output.originality_score
        flag_count = len(originality_output.flags)

        if os_ >= 0.8:
            reward = 1.0
            breakdown = f"Highly original (score={os_:.2f}). No dominant template patterns."
        elif os_ >= 0.6:
            reward = os_
            breakdown = f"Moderately original (score={os_:.2f}). Some template overlap detected."
        elif os_ >= 0.4:
            reward = 0.3
            breakdown = f"Generic content (score={os_:.2f}). Multiple overused patterns present."
        else:
            reward = 0.0
            breakdown = f"Template clone (score={os_:.2f}). Script heavily relies on overused formats."

        return OriginalityRewardResult(
            score=reward,
            originality_score=os_,
            flag_count=flag_count,
            breakdown=breakdown,
        )
