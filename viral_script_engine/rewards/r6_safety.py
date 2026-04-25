from pydantic import BaseModel

from viral_script_engine.agents.moderation_agent import ModerationOutput


class SafetyRewardResult(BaseModel):
    score: float
    flag_count: int
    highest_severity: str
    breakdown: str


class SafetyReward:
    """
    Converts ModerationOutput into a reward signal.

    Scoring:
    - Zero flags:                    1.0
    - Only low-severity flags:       0.8
    - Any medium-severity flag:      0.5
    - Any high-severity flag:        0.0  (hard zero — non-negotiable per platform policy)
    """

    def score(self, moderation_output: ModerationOutput) -> SafetyRewardResult:
        if moderation_output.total_flags == 0:
            return SafetyRewardResult(
                score=1.0,
                flag_count=0,
                highest_severity="none",
                breakdown="No flags detected.",
            )

        severities = [f.severity for f in moderation_output.flags]
        if "high" in severities:
            highest = "high"
            reward = 0.0
            breakdown = "Hard zero: high-severity flag present (platform policy violation)."
        elif "medium" in severities:
            highest = "medium"
            reward = 0.5
            breakdown = f"Medium-severity flags detected ({moderation_output.total_flags} total)."
        else:
            highest = "low"
            reward = 0.8
            breakdown = f"Only low-severity flags detected ({moderation_output.total_flags} total)."

        return SafetyRewardResult(
            score=reward,
            flag_count=moderation_output.total_flags,
            highest_severity=highest,
            breakdown=breakdown,
        )
