from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from viral_script_engine.agents.critic import CritiqueClaim
from viral_script_engine.environment.actions import ArbitratorAction

_WEIGHTS: Dict[str, float] = {
    "r1": 0.20, "r2": 0.15, "r3": 0.15, "r4": 0.15, "r5": 0.15,
    "r6": 0.10, "r7": 0.10,
}


class RewardComponents(BaseModel):
    r1_hook_strength: Optional[float] = None
    r2_coherence: Optional[float] = None
    r3_cultural_alignment: Optional[float] = None
    r4_debate_resolution: Optional[float] = None
    r5_defender_preservation: Optional[float] = None
    r6_safety: Optional[float] = None
    r7_originality: Optional[float] = None
    anti_gaming_penalty: float = 0.0
    total: float = 0.0

    def compute_total(self) -> float:
        vals = {
            "r1": self.r1_hook_strength,
            "r2": self.r2_coherence,
            "r3": self.r3_cultural_alignment,
            "r4": self.r4_debate_resolution,
            "r5": self.r5_defender_preservation,
            "r6": self.r6_safety,
            "r7": self.r7_originality,
        }
        active = {k: v for k, v in vals.items() if v is not None}
        if not active:
            self.total = 0.0
            return 0.0
        norm = sum(_WEIGHTS[k] for k in active)
        weighted = sum(_WEIGHTS[k] * v for k, v in active.items()) / norm
        self.total = max(0.0, min(1.0, weighted - self.anti_gaming_penalty))
        return self.total


class DebateRound(BaseModel):
    step_num: int
    critic_claims: List[CritiqueClaim]
    defender_response: Optional[Any] = None
    arbitrator_action: Optional[ArbitratorAction] = None
    rewrite_diff: Optional[str] = None
    reward_components: Optional[RewardComponents] = None
    moderation_output: Optional[Any] = None
    originality_output: Optional[Any] = None


class Observation(BaseModel):
    current_script: str
    original_script: str
    region: str
    platform: str
    niche: str
    step_num: int
    max_steps: int
    debate_history: List[DebateRound]
    reward_components: RewardComponents
    difficulty_level: str
    episode_id: str
    current_moderation_flags: List[Any] = []
    current_originality_flags: List[Any] = []
