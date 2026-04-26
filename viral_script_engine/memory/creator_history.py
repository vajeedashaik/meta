from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class EpisodeMemory(BaseModel):
    episode_id: str
    episode_number: int
    script_niche: str
    platform: str
    dominant_flaw: str
    actions_taken: List[str]
    what_worked: List[str]
    what_didnt: List[str]
    final_total_reward: float
    key_learning: str


class CreatorHistoryBuffer(BaseModel):
    creator_id: str
    total_episodes: int
    recent_episodes: List[EpisodeMemory]        # sliding window of last 5
    recurring_weak_points: List[str]            # dominant_flaw in >= 3 of last 5
    recurring_strong_points: List[str]          # reward component >= 0.7 in >= 4 of last 5
    most_effective_action: Optional[str]        # action_type with highest avg reward delta
    voice_stability_score: float                # consistency of R3 (0–1)
    improvement_trend: str                      # "improving" | "plateauing" | "declining"

    def to_prompt_context(self) -> str:
        n = len(self.recent_episodes)
        if n == 0:
            return "CREATOR HISTORY: No sessions recorded yet."

        last = self.recent_episodes[-1]
        weak = ", ".join(self.recurring_weak_points) if self.recurring_weak_points else "none"
        strong = ", ".join(self.recurring_strong_points) if self.recurring_strong_points else "none"
        effective = self.most_effective_action or "unknown"
        last_action = last.actions_taken[0] if last.actions_taken else "unknown"

        return (
            f"CREATOR HISTORY (last {n} session{'s' if n != 1 else ''}):\n"
            f"Recurring weak points: {weak}\n"
            f"Recurring strengths: {strong}\n"
            f"Most effective fix: {effective}\n"
            f"Voice stability: {self.voice_stability_score:.0%}\n"
            f"Trend: {self.improvement_trend}\n"
            f"Last session: fixed {last.dominant_flaw} with {last_action}, "
            f"reward {last.final_total_reward:.2f}"
        )
