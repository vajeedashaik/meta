from typing import List

from pydantic import BaseModel

from viral_script_engine.agents.critic import CritiqueClaim
from viral_script_engine.agents.defender import DefenderOutput
from viral_script_engine.agents.reasoning_parser import ReasoningChain
from viral_script_engine.environment.observations import RewardComponents
from viral_script_engine.rewards.process_verifier import ProcessVerifier


class ProcessRewardResult(BaseModel):
    process_score: float
    priority_score: float
    conflict_score: float
    defender_score: float
    weighted_contribution: float


class ProcessReward:
    """
    Combines the three process verification scores into a single
    process reward signal that fires BEFORE the rewrite executes.

    Weights:
    - priority_assessment: 0.40
    - conflict_check:       0.35
    - defender_consideration: 0.25

    The process reward contributes 0.15 of total step reward so outcome
    still dominates and the Arbitrator cannot game process rewards alone.
    """

    PROCESS_WEIGHT = 0.15

    _PRIORITY_W = 0.40
    _CONFLICT_W = 0.35
    _DEFENDER_W = 0.25

    def __init__(self):
        self.verifier = ProcessVerifier()

    def score(
        self,
        reasoning_chain: ReasoningChain,
        critic_claims: List[CritiqueClaim],
        defender_output: DefenderOutput,
        current_reward_components: RewardComponents,
        episode_start_components: RewardComponents,
    ) -> ProcessRewardResult:
        """
        Returns ProcessRewardResult with individual check scores and
        the weighted_contribution to add to the total step reward.
        """
        priority_score = self.verifier.verify_priority_assessment(
            priority_assessment=reasoning_chain.priority_assessment,
            critic_claims=critic_claims,
            current_reward_components=current_reward_components,
        )
        conflict_score = self.verifier.verify_conflict_check(
            conflict_check_answer=reasoning_chain.conflict_check_answer,
            conflict_check_reason=reasoning_chain.conflict_check_reason,
            action=reasoning_chain.action,
            current_reward_components=current_reward_components,
            episode_start_components=episode_start_components,
        )
        defender_score = self.verifier.verify_defender_consideration(
            defender_consideration_answer=reasoning_chain.defender_consideration_answer,
            defender_consideration_reason=reasoning_chain.defender_consideration_reason,
            action=reasoning_chain.action,
            defender_output=defender_output,
        )

        process_score = (
            self._PRIORITY_W * priority_score
            + self._CONFLICT_W * conflict_score
            + self._DEFENDER_W * defender_score
        )
        weighted_contribution = process_score * self.PROCESS_WEIGHT

        return ProcessRewardResult(
            process_score=process_score,
            priority_score=priority_score,
            conflict_score=conflict_score,
            defender_score=defender_score,
            weighted_contribution=weighted_contribution,
        )
