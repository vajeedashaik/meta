from __future__ import annotations

import math
from collections import Counter
from typing import Dict, List, Optional

from viral_script_engine.memory.creator_history import CreatorHistoryBuffer, EpisodeMemory

_REWARD_KEYS = [
    "r1_hook_strength",
    "r2_coherence",
    "r3_cultural_alignment",
    "r4_debate_resolution",
    "r5_defender_preservation",
    "r6_safety",
    "r7_originality",
    "r8_persona_fit",
    "r9_platform_pacing",
]

_DELTA_THRESHOLD = 0.05


class MemoryCompressor:
    """
    Compresses a completed episode into a structured EpisodeMemory.
    Called at the end of every episode, before the next reset().
    Zero LLM calls — all compression is rule-based.
    """

    def compress(self, episode_log: dict, episode_number: int) -> EpisodeMemory:
        """
        episode_log fields expected:
          episode_id, niche, platform, first_critique_claims,
          actions_taken, initial_reward_components, final_reward_components,
          final_total_reward
        """
        episode_id = episode_log.get("episode_id", "unknown")
        niche = episode_log.get("niche", "unknown")
        platform = episode_log.get("platform", "unknown")
        actions_taken: List[str] = episode_log.get("actions_taken", [])
        initial_rc: dict = episode_log.get("initial_reward_components", {})
        final_rc: dict = episode_log.get("final_reward_components", {})
        final_total = episode_log.get("final_total_reward", 0.0)

        # 1. dominant_flaw: most common critique_class from first-step claims
        first_claims = episode_log.get("first_critique_claims", [])
        if first_claims:
            counts = Counter(
                c.get("critique_class", "unknown") for c in first_claims
            )
            dominant_flaw = counts.most_common(1)[0][0]
        else:
            dominant_flaw = "hook_weakness"

        # 2. what_worked / what_didnt — reward components with significant delta
        what_worked: List[str] = []
        what_didnt: List[str] = []
        for key in _REWARD_KEYS:
            init_val = initial_rc.get(key)
            final_val = final_rc.get(key)
            if init_val is None or final_val is None:
                continue
            delta = final_val - init_val
            if delta > _DELTA_THRESHOLD:
                what_worked.append(key)
            elif delta < -_DELTA_THRESHOLD:
                what_didnt.append(key)

        # 3. key_learning — rule-based template
        most_used_action = (
            Counter(actions_taken).most_common(1)[0][0] if actions_taken else "no_action"
        )
        worked_str = what_worked[0] if what_worked else "no component"
        didnt_str = what_didnt[0] if what_didnt else "no regressions"
        key_learning = (
            f"Fixed {dominant_flaw} using {most_used_action}. "
            f"{worked_str} improved, {didnt_str}."
        )

        return EpisodeMemory(
            episode_id=episode_id,
            episode_number=episode_number,
            script_niche=niche,
            platform=platform,
            dominant_flaw=dominant_flaw,
            actions_taken=actions_taken,
            what_worked=what_worked,
            what_didnt=what_didnt,
            final_total_reward=final_total,
            key_learning=key_learning,
        )

    def update_buffer(
        self,
        existing_buffer: Optional[CreatorHistoryBuffer],
        new_memory: EpisodeMemory,
        creator_id: str,
    ) -> CreatorHistoryBuffer:
        """
        Adds new_memory to the buffer, maintaining a sliding window of 5.
        Recomputes all aggregate stats.
        """
        if existing_buffer is None:
            episodes: List[EpisodeMemory] = []
            total = 0
        else:
            episodes = list(existing_buffer.recent_episodes)
            total = existing_buffer.total_episodes

        episodes.append(new_memory)
        if len(episodes) > 5:
            episodes = episodes[-5:]  # keep last 5
        total += 1

        # recurring_weak_points: dominant_flaw in >= 3 of last 5
        flaw_counts = Counter(ep.dominant_flaw for ep in episodes)
        recurring_weak_points = [
            flaw for flaw, cnt in flaw_counts.items() if cnt >= 3
        ]

        # recurring_strong_points: reward component >= 0.7 in >= 4 of last 5
        recurring_strong_points = self._compute_strong_points(episodes)

        # most_effective_action: action_type with highest avg final_total_reward
        most_effective_action = self._compute_most_effective_action(episodes)

        # voice_stability_score: 1 - std_dev of r3 across episodes (inverted, clamped)
        voice_stability_score = self._compute_voice_stability(episodes)

        # improvement_trend: slope of final_total_reward
        improvement_trend = self._compute_trend(episodes)

        return CreatorHistoryBuffer(
            creator_id=creator_id,
            total_episodes=total,
            recent_episodes=episodes,
            recurring_weak_points=recurring_weak_points,
            recurring_strong_points=recurring_strong_points,
            most_effective_action=most_effective_action,
            voice_stability_score=voice_stability_score,
            improvement_trend=improvement_trend,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _compute_strong_points(self, episodes: List[EpisodeMemory]) -> List[str]:
        """Reward components consistently >= 0.7 in >= 4 of last 5 episodes."""
        if not episodes:
            return []
        # We only know what_worked from EpisodeMemory — approximate by checking
        # which components appear in what_worked across >= 4 episodes
        counts: Dict[str, int] = {}
        for ep in episodes:
            for comp in ep.what_worked:
                counts[comp] = counts.get(comp, 0) + 1
        threshold = max(4, len(episodes) - 1) if len(episodes) >= 4 else len(episodes)
        return [comp for comp, cnt in counts.items() if cnt >= threshold]

    def _compute_most_effective_action(self, episodes: List[EpisodeMemory]) -> Optional[str]:
        """Action type with highest average final_total_reward across episodes it appeared in."""
        if not episodes:
            return None
        action_rewards: Dict[str, List[float]] = {}
        for ep in episodes:
            for action in set(ep.actions_taken):
                action_rewards.setdefault(action, []).append(ep.final_total_reward)
        if not action_rewards:
            return None
        return max(action_rewards, key=lambda a: sum(action_rewards[a]) / len(action_rewards[a]))

    def _compute_voice_stability(self, episodes: List[EpisodeMemory]) -> float:
        """Stability of R3 inferred from whether r3_cultural_alignment was in what_didnt.
        A proxy: episodes where R3 did NOT regress count toward stability."""
        if not episodes:
            return 1.0
        stable_count = sum(
            1 for ep in episodes if "r3_cultural_alignment" not in ep.what_didnt
        )
        return stable_count / len(episodes)

    def _compute_trend(self, episodes: List[EpisodeMemory]) -> str:
        """Slope of final_total_reward across the episode window."""
        if len(episodes) < 2:
            return "plateauing"
        rewards = [ep.final_total_reward for ep in episodes]
        n = len(rewards)
        x_mean = (n - 1) / 2.0
        y_mean = sum(rewards) / n
        numerator = sum((i - x_mean) * (rewards[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        if denominator == 0:
            return "plateauing"
        slope = numerator / denominator
        if slope > 0.02:
            return "improving"
        elif slope < -0.02:
            return "declining"
        return "plateauing"
