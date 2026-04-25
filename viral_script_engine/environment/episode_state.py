from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from typing import List

from viral_script_engine.environment.actions import ActionType
from viral_script_engine.environment.observations import DebateRound, RewardComponents


@dataclass
class EpisodeState:
    episode_id: str
    original_script: str
    current_script: str
    region: str
    platform: str
    niche: str
    step_num: int
    max_steps: int
    debate_history: List[DebateRound]
    episode_start_rewards: RewardComponents
    last_reward_components: RewardComponents
    difficulty_level: str
    action_history: List[ActionType]

    @classmethod
    def new(
        cls,
        script: dict,
        max_steps: int,
        difficulty_level: str,
        initial_rewards: RewardComponents,
    ) -> EpisodeState:
        return cls(
            episode_id=str(uuid.uuid4()),
            original_script=script["script_text"],
            current_script=script["script_text"],
            region=script["region"],
            platform=script["platform"],
            niche=script["niche"],
            step_num=0,
            max_steps=max_steps,
            debate_history=[],
            episode_start_rewards=initial_rewards,
            last_reward_components=initial_rewards,
            difficulty_level=difficulty_level,
            action_history=[],
        )
