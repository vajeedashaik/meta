import logging
from typing import List, Optional, Tuple

from pydantic import BaseModel

from viral_script_engine.environment.actions import ActionType
from viral_script_engine.environment.observations import RewardComponents

logger = logging.getLogger(__name__)

_COMPONENT_FIELDS = [
    "r1_hook_strength", "r2_coherence", "r3_cultural_alignment",
    "r4_debate_resolution", "r5_defender_preservation",
    "r6_safety", "r7_originality", "r8_persona_fit", "r9_platform_pacing",
]

_DROP_THRESHOLD = 0.25


class AntiGamingLog(BaseModel):
    episode_id: str
    step_num: int
    triggered: bool
    rule_triggered: Optional[str] = None
    component_that_dropped: Optional[str] = None
    penalty_applied: float
    pre_penalty_total: float
    post_penalty_total: float


class RewardAggregator:
    def compute(
        self,
        components: RewardComponents,
        episode_start_components: RewardComponents,
        action_history: List[ActionType],
        episode_id: str = "",
        step_num: int = 0,
    ) -> Tuple[RewardComponents, AntiGamingLog]:
        # Hard zero: if R6 (safety) is 0.0, the entire step reward is zeroed out
        # regardless of other component scores — any shadowban trigger is non-negotiable.
        if components.r6_safety is not None and components.r6_safety == 0.0:
            components.compute_total()
            pre_penalty_total = components.total
            components.total = 0.0
            components.anti_gaming_penalty = 1.0
            logger.warning("R6 safety hard zero triggered — shadowban content detected, zeroing step reward.")
            log = AntiGamingLog(
                episode_id=episode_id,
                step_num=step_num,
                triggered=True,
                rule_triggered="r6_safety_hard_zero",
                component_that_dropped="r6_safety",
                penalty_applied=1.0,
                pre_penalty_total=pre_penalty_total,
                post_penalty_total=0.0,
            )
            return components, log

        components.compute_total()
        # Phase 7: add process reward additively before anti-gaming checks
        if components.process_reward is not None and components.process_reward > 0:
            components.total = min(1.0, components.total + components.process_reward)
        pre_penalty_total = components.total

        for field in _COMPONENT_FIELDS:
            curr = getattr(components, field)
            start = getattr(episode_start_components, field)
            if curr is not None and start is not None and curr < start - _DROP_THRESHOLD:
                logger.warning("Catastrophic drop in %s: %.3f -> %.3f", field, start, curr)
                components.total = 0.0
                components.anti_gaming_penalty = start - curr
                log = AntiGamingLog(
                    episode_id=episode_id,
                    step_num=step_num,
                    triggered=True,
                    rule_triggered="catastrophic_drop",
                    component_that_dropped=field,
                    penalty_applied=components.anti_gaming_penalty,
                    pre_penalty_total=pre_penalty_total,
                    post_penalty_total=0.0,
                )
                return components, log

        penalty = 0.0
        if len(action_history) >= 3 and len(set(action_history[-3:])) == 1:
            penalty = 0.15
            logger.warning("Action diversity penalty: last 3 actions all %s", action_history[-1])

        components.anti_gaming_penalty = penalty
        components.total = max(0.0, min(1.0, components.total - penalty))

        log = AntiGamingLog(
            episode_id=episode_id,
            step_num=step_num,
            triggered=penalty > 0,
            rule_triggered="action_repetition" if penalty > 0 else None,
            component_that_dropped=None,
            penalty_applied=penalty,
            pre_penalty_total=pre_penalty_total,
            post_penalty_total=components.total,
        )
        return components, log
