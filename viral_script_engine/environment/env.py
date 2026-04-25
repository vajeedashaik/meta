import json
import random
from typing import Optional, Tuple

from viral_script_engine.agents.critic import CriticAgent
from viral_script_engine.agents.rewriter import RewriterAgent
from viral_script_engine.environment.actions import ArbitratorAction
from viral_script_engine.environment.episode_state import EpisodeState
from viral_script_engine.environment.observations import (
    DebateRound, Observation, RewardComponents,
)
from viral_script_engine.rewards.r1_hook_strength import HookStrengthReward
from viral_script_engine.rewards.r2_coherence import CoherenceReward
from viral_script_engine.rewards.reward_aggregator import RewardAggregator

_TIERS = {
    "easy": ["S01", "S02", "S03", "S04"],
    "medium": ["S05", "S06", "S07"],
    "hard": ["S08", "S09", "S10"],
    "self_generated": [],
}


class ViralScriptEnv:
    def __init__(
        self,
        scripts_path: str = "data/test_scripts/scripts.json",
        max_steps: int = 5,
        difficulty: str = "easy",
        use_anti_gaming: bool = True,
    ):
        self.max_steps = max_steps
        self.difficulty = difficulty
        self.use_anti_gaming = use_anti_gaming

        with open(scripts_path) as f:
            all_scripts = json.load(f)

        tier_ids = _TIERS[difficulty]
        self._scripts = [s for s in all_scripts if s["script_id"] in tier_ids]
        self.critic = CriticAgent()
        self.rewriter = RewriterAgent()
        self.r1 = HookStrengthReward()
        self.r2 = CoherenceReward()
        self.aggregator = RewardAggregator()
        self._state: Optional[EpisodeState] = None

    def reset(self, seed=None, options=None) -> Tuple[dict, dict]:
        if seed is not None:
            random.seed(seed)
        script = random.choice(self._scripts)

        r1_result = self.r1.score(script["script_text"])
        r2_result = self.r2.score(script["script_text"], script["script_text"])
        initial_rewards = RewardComponents(
            r1_hook_strength=r1_result.score,
            r2_coherence=r2_result.score,
        )
        initial_rewards.compute_total()

        self._state = EpisodeState.new(
            script=script,
            max_steps=self.max_steps,
            difficulty_level=self.difficulty,
            initial_rewards=initial_rewards,
        )
        return self._build_observation().model_dump(), {}

    def step(self, action: dict) -> Tuple[dict, float, bool, bool, dict]:
        if self._state is None:
            raise RuntimeError("Call reset() before step()")

        arb_action = ArbitratorAction(**action)

        critique = self.critic.critique(
            script=self._state.current_script,
            region=self._state.region,
            platform=self._state.platform,
            niche=self._state.niche,
        )

        rewrite_result = self.rewriter.rewrite(self._state.current_script, arb_action)
        new_script = rewrite_result.rewritten_script

        r1_result = self.r1.score(new_script)
        r2_result = self.r2.score(self._state.original_script, new_script)
        components = RewardComponents(
            r1_hook_strength=r1_result.score,
            r2_coherence=r2_result.score,
        )

        self._state.action_history.append(arb_action.action_type)
        if self.use_anti_gaming:
            components = self.aggregator.compute(
                components, self._state.episode_start_rewards, self._state.action_history
            )
        else:
            components.compute_total()

        round_ = DebateRound(
            step_num=self._state.step_num,
            critic_claims=critique.claims,
            arbitrator_action=arb_action,
            rewrite_diff=rewrite_result.diff,
            reward_components=components,
        )
        self._state.debate_history.append(round_)
        self._state.current_script = new_script
        self._state.last_reward_components = components
        self._state.step_num += 1

        terminated = (
            self._state.step_num >= self._state.max_steps
            or components.total >= 0.9
        )
        info = {
            "reward_components": components.model_dump(),
            "anti_gaming_triggered": components.anti_gaming_penalty > 0,
            "penalty_reason": "anti_gaming" if components.anti_gaming_penalty > 0 else None,
        }
        return self._build_observation().model_dump(), components.total, terminated, False, info

    def state(self) -> dict:
        if self._state is None:
            return {}
        s = self._state
        return {
            "current_script": s.current_script,
            "original_script": s.original_script,
            "debate_history": [r.model_dump() for r in s.debate_history],
            "reward_components": s.last_reward_components.model_dump(),
            "step_num": s.step_num,
            "difficulty_level": s.difficulty_level,
            "episode_id": s.episode_id,
        }

    def _build_observation(self) -> Observation:
        s = self._state
        return Observation(
            current_script=s.current_script,
            original_script=s.original_script,
            region=s.region,
            platform=s.platform,
            niche=s.niche,
            step_num=s.step_num,
            max_steps=s.max_steps,
            debate_history=s.debate_history,
            reward_components=s.last_reward_components,
            difficulty_level=s.difficulty_level,
            episode_id=s.episode_id,
        )
