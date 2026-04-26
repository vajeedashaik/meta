from __future__ import annotations
import math
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from viral_script_engine.environment.trajectory import Trajectory


class ContrastiveRewardResult(BaseModel):
    final_reward: float
    base_reward: float
    contrast_bonus: float
    delta: float
    winning_trajectory: str        # "A" | "B" | "tie"
    winning_trajectory_type: str   # "critic_first" | "defender_first" | "tie"


class ContrastiveReward:
    """
    Computes a reward based on the delta between two parallel trajectories.

    The key insight: the Arbitrator is rewarded not just for doing well,
    but for doing BETTER than the counterfactual alternative.

    Reward formula:
    - delta = traj_a.cumulative_reward - traj_b.cumulative_reward
    - base_reward = max(traj_a.cumulative_reward, traj_b.cumulative_reward)
      (reward the better trajectory's absolute performance)
    - contrast_bonus = tanh(delta * 3) * 0.2
      (add up to +0.2 bonus when one trajectory clearly dominates)
    - final = base_reward + contrast_bonus, clipped to [0, 1]

    When delta is near zero, contrast_bonus → 0 — no extra credit for
    a coin-flip decision.  When delta is large, contrast_bonus is maximised —
    this is the signal that matters most for learning action ordering.
    """

    def compute(
        self,
        traj_a: "Trajectory",
        traj_b: "Trajectory",
    ) -> ContrastiveRewardResult:
        delta = traj_a.cumulative_reward - traj_b.cumulative_reward
        base_reward = max(traj_a.cumulative_reward, traj_b.cumulative_reward)
        contrast_bonus = math.tanh(delta * 3) * 0.2
        final = max(0.0, min(1.0, base_reward + contrast_bonus))

        if abs(delta) < 1e-6:
            winning = "tie"
            winning_type = "tie"
        elif delta > 0:
            winning = "A"
            winning_type = traj_a.trajectory_type
        else:
            winning = "B"
            winning_type = traj_b.trajectory_type

        return ContrastiveRewardResult(
            final_reward=final,
            base_reward=base_reward,
            contrast_bonus=contrast_bonus,
            delta=delta,
            winning_trajectory=winning,
            winning_trajectory_type=winning_type,
        )
