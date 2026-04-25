import logging
from typing import List

from viral_script_engine.environment.actions import ActionType
from viral_script_engine.environment.observations import RewardComponents

logger = logging.getLogger(__name__)

_COMPONENT_FIELDS = [
    "r1_hook_strength", "r2_coherence", "r3_cultural_alignment",
    "r4_debate_resolution", "r5_defender_preservation",
]


class RewardAggregator:
    def compute(
        self,
        components: RewardComponents,
        episode_start_components: RewardComponents,
        action_history: List[ActionType],
    ) -> RewardComponents:
        components.compute_total()

        # Anti-gaming rule 1: catastrophic drop (>0.2 drop in any component)
        for field in _COMPONENT_FIELDS:
            curr = getattr(components, field)
            start = getattr(episode_start_components, field)
            if curr is not None and start is not None and curr < start - 0.2:
                logger.warning("Catastrophic drop in %s: %.3f -> %.3f", field, start, curr)
                components.total = 0.0
                components.anti_gaming_penalty = start - curr
                return components

        # Anti-gaming rule 2: action diversity (last 3 same ActionType)
        penalty = 0.0
        if len(action_history) >= 3 and len(set(action_history[-3:])) == 1:
            penalty = 0.15
            logger.warning("Action diversity penalty: last 3 actions all %s", action_history[-1])

        components.anti_gaming_penalty = penalty
        components.total = max(0.0, min(1.0, components.total - penalty))
        return components
