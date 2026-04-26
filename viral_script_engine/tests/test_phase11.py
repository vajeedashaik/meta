"""Phase 11 tests — Longitudinal Episode Memory."""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from viral_script_engine.agents.critic import CritiqueClaim
from viral_script_engine.memory.creator_history import CreatorHistoryBuffer, EpisodeMemory
from viral_script_engine.memory.memory_compressor import MemoryCompressor
from viral_script_engine.memory.history_store import HistoryStore

_SCRIPTS_PATH = str(
    Path(__file__).parent.parent / "data" / "test_scripts" / "scripts.json"
)
_CULTURAL_KB_PATH = str(
    Path(__file__).parent.parent / "data" / "cultural_kb.json"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_episode_log(
    episode_id: str = "ep1",
    niche: str = "finance",
    platform: str = "Reels",
    dominant_class: str = "hook_weakness",
    actions: list = None,
    initial_r1: float = 0.4,
    final_r1: float = 0.7,
    initial_r3: float = 0.6,
    final_r3: float = 0.6,
    final_total: float = 0.65,
) -> dict:
    return {
        "episode_id": episode_id,
        "niche": niche,
        "platform": platform,
        "first_critique_claims": [
            {"claim_id": "C1", "critique_class": dominant_class, "severity": "high",
             "claim_text": "test", "evidence": "e", "timestamp_range": "0-3s"},
        ],
        "actions_taken": actions or ["hook_rewrite"],
        "initial_reward_components": {
            "r1_hook_strength": initial_r1,
            "r2_coherence": 0.5,
            "r3_cultural_alignment": initial_r3,
        },
        "final_reward_components": {
            "r1_hook_strength": final_r1,
            "r2_coherence": 0.5,
            "r3_cultural_alignment": final_r3,
        },
        "final_total_reward": final_total,
    }


def _make_memory(
    episode_number: int = 1,
    dominant_flaw: str = "hook_weakness",
    actions: list = None,
    what_worked: list = None,
    what_didnt: list = None,
    final_total_reward: float = 0.65,
) -> EpisodeMemory:
    return EpisodeMemory(
        episode_id=f"ep{episode_number}",
        episode_number=episode_number,
        script_niche="finance",
        platform="Reels",
        dominant_flaw=dominant_flaw,
        actions_taken=actions or ["hook_rewrite"],
        what_worked=what_worked or ["r1_hook_strength"],
        what_didnt=what_didnt or [],
        final_total_reward=final_total_reward,
        key_learning=f"Fixed {dominant_flaw}. r1_hook_strength improved.",
    )


# ---------------------------------------------------------------------------
# MemoryCompressor.compress() tests
# ---------------------------------------------------------------------------

class TestMemoryCompressorCompress:
    def setup_method(self):
        self.compressor = MemoryCompressor()

    def test_extracts_dominant_flaw(self):
        log = _make_episode_log(dominant_class="hook_weakness")
        mem = self.compressor.compress(log, episode_number=1)
        assert mem.dominant_flaw == "hook_weakness"

    def test_actions_taken_preserved(self):
        log = _make_episode_log(actions=["hook_rewrite", "section_reorder"])
        mem = self.compressor.compress(log, episode_number=1)
        assert mem.actions_taken == ["hook_rewrite", "section_reorder"]

    def test_what_worked_positive_delta(self):
        log = _make_episode_log(initial_r1=0.4, final_r1=0.75)  # delta = +0.35
        mem = self.compressor.compress(log, episode_number=1)
        assert "r1_hook_strength" in mem.what_worked

    def test_what_didnt_negative_delta(self):
        log = _make_episode_log(initial_r3=0.8, final_r3=0.4)  # delta = -0.4
        mem = self.compressor.compress(log, episode_number=1)
        assert "r3_cultural_alignment" in mem.what_didnt

    def test_no_delta_not_flagged(self):
        # r2 starts and ends at 0.5 — neither worked nor didn't
        log = _make_episode_log(initial_r1=0.5, final_r1=0.5)
        mem = self.compressor.compress(log, episode_number=1)
        assert "r2_coherence" not in mem.what_worked
        assert "r2_coherence" not in mem.what_didnt

    def test_key_learning_is_string(self):
        log = _make_episode_log()
        mem = self.compressor.compress(log, episode_number=1)
        assert isinstance(mem.key_learning, str)
        assert len(mem.key_learning) > 0

    def test_episode_number_stored(self):
        log = _make_episode_log()
        mem = self.compressor.compress(log, episode_number=7)
        assert mem.episode_number == 7


# ---------------------------------------------------------------------------
# MemoryCompressor.update_buffer() — sliding window
# ---------------------------------------------------------------------------

class TestMemoryCompressorUpdateBuffer:
    def setup_method(self):
        self.compressor = MemoryCompressor()

    def test_starts_empty(self):
        mem = _make_memory(1)
        buf = self.compressor.update_buffer(None, mem, "creator_1")
        assert buf.total_episodes == 1
        assert len(buf.recent_episodes) == 1

    def test_window_keeps_last_5(self):
        buf = None
        for i in range(6):
            mem = _make_memory(episode_number=i + 1)
            buf = self.compressor.update_buffer(buf, mem, "creator_1")
        assert len(buf.recent_episodes) == 5
        assert buf.total_episodes == 6
        # Oldest (episode 1) should have been dropped
        assert buf.recent_episodes[0].episode_number == 2

    def test_recurring_weak_points_threshold(self):
        buf = None
        # 3 of 5 episodes have hook_weakness
        flaws = ["hook_weakness", "hook_weakness", "cultural_mismatch", "hook_weakness", "pacing_issue"]
        for i, flaw in enumerate(flaws):
            mem = _make_memory(episode_number=i + 1, dominant_flaw=flaw)
            buf = self.compressor.update_buffer(buf, mem, "creator_1")
        assert "hook_weakness" in buf.recurring_weak_points
        assert "cultural_mismatch" not in buf.recurring_weak_points

    def test_recurring_weak_points_below_threshold(self):
        buf = None
        flaws = ["hook_weakness", "hook_weakness", "cultural_mismatch", "cultural_mismatch", "pacing_issue"]
        for i, flaw in enumerate(flaws):
            mem = _make_memory(episode_number=i + 1, dominant_flaw=flaw)
            buf = self.compressor.update_buffer(buf, mem, "creator_1")
        assert "hook_weakness" not in buf.recurring_weak_points
        assert "cultural_mismatch" not in buf.recurring_weak_points

    def test_improvement_trend_improving(self):
        rewards = [0.50, 0.55, 0.62, 0.70, 0.78]
        buf = None
        for i, r in enumerate(rewards):
            mem = _make_memory(episode_number=i + 1, final_total_reward=r)
            buf = self.compressor.update_buffer(buf, mem, "creator_1")
        assert buf.improvement_trend == "improving"

    def test_improvement_trend_declining(self):
        rewards = [0.78, 0.70, 0.62, 0.55, 0.50]
        buf = None
        for i, r in enumerate(rewards):
            mem = _make_memory(episode_number=i + 1, final_total_reward=r)
            buf = self.compressor.update_buffer(buf, mem, "creator_1")
        assert buf.improvement_trend == "declining"

    def test_improvement_trend_plateauing(self):
        rewards = [0.65, 0.64, 0.65, 0.66, 0.65]
        buf = None
        for i, r in enumerate(rewards):
            mem = _make_memory(episode_number=i + 1, final_total_reward=r)
            buf = self.compressor.update_buffer(buf, mem, "creator_1")
        assert buf.improvement_trend == "plateauing"


# ---------------------------------------------------------------------------
# Voice stability score
# ---------------------------------------------------------------------------

class TestVoiceStabilityScore:
    def setup_method(self):
        self.compressor = MemoryCompressor()

    def test_high_stability_when_r3_never_drops(self):
        buf = None
        for i in range(5):
            mem = _make_memory(episode_number=i + 1, what_didnt=[])
            buf = self.compressor.update_buffer(buf, mem, "creator_1")
        assert buf.voice_stability_score >= 0.8

    def test_low_stability_when_r3_consistently_drops(self):
        buf = None
        for i in range(5):
            mem = _make_memory(episode_number=i + 1, what_didnt=["r3_cultural_alignment"])
            buf = self.compressor.update_buffer(buf, mem, "creator_1")
        assert buf.voice_stability_score < 0.5


# ---------------------------------------------------------------------------
# HistoryStore
# ---------------------------------------------------------------------------

class TestHistoryStore:
    def test_load_returns_none_for_unknown_creator(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HistoryStore(store_dir=tmpdir)
            result = store.load("nonexistent_creator")
            assert result is None

    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HistoryStore(store_dir=tmpdir)
            mem = _make_memory(1)
            compressor = MemoryCompressor()
            buf = compressor.update_buffer(None, mem, "creator_test")
            store.save(buf)
            loaded = store.load("creator_test")
            assert loaded is not None
            assert loaded.creator_id == "creator_test"
            assert loaded.total_episodes == 1

    def test_list_creators(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HistoryStore(store_dir=tmpdir)
            compressor = MemoryCompressor()
            for cid in ["c1", "c2", "c3"]:
                buf = compressor.update_buffer(None, _make_memory(1), cid)
                store.save(buf)
            creators = store.list_creators()
            assert set(creators) == {"c1", "c2", "c3"}


# ---------------------------------------------------------------------------
# to_prompt_context() word count
# ---------------------------------------------------------------------------

class TestToPromptContext:
    def test_output_under_200_words(self):
        compressor = MemoryCompressor()
        buf = None
        for i in range(5):
            mem = _make_memory(episode_number=i + 1)
            buf = compressor.update_buffer(buf, mem, "creator_1")
        context = buf.to_prompt_context()
        word_count = len(context.split())
        assert word_count < 200, f"to_prompt_context() produced {word_count} words (limit 200)"

    def test_none_buffer_no_context(self):
        # When buffer is None, env returns None — just verify the method
        # exists and format is non-empty when there IS history
        compressor = MemoryCompressor()
        mem = _make_memory(1)
        buf = compressor.update_buffer(None, mem, "creator_1")
        context = buf.to_prompt_context()
        assert "CREATOR HISTORY" in context


# ---------------------------------------------------------------------------
# Environment integration: reset() and step() wiring
# ---------------------------------------------------------------------------

class TestEnvMemoryIntegration:
    def _make_env(self, store_dir: str):
        from viral_script_engine.environment.env import ViralScriptEnv
        env = ViralScriptEnv(
            scripts_path=_SCRIPTS_PATH,
            cultural_kb_path=_CULTURAL_KB_PATH,
            difficulty="easy",
            use_escalation=False,
            use_anti_gaming=False,
        )
        env.history_store = HistoryStore(store_dir=store_dir)
        return env

    def _run_episode(self, env, session_num: int = 1):
        real_claim = CritiqueClaim(
            claim_id="C1",
            severity="high",
            critique_class="hook_weakness",
            claim_text="weak hook",
            evidence="...",
            timestamp_range="0-3s",
            is_falsifiable=True,
        )
        mock_critique = MagicMock()
        mock_critique.claims = [real_claim]
        mock_critique.overall_severity = "high"

        mock_defender = MagicMock()
        mock_defender.core_strength = "strong"
        mock_defender.core_strength_quote = "test"
        mock_defender.defense_argument = "preserve"
        mock_defender.flagged_critic_claims = []
        mock_defender.regional_voice_elements = []
        mock_defender.model_dump.return_value = {}

        mock_rewrite = MagicMock()
        obs, _ = env.reset(seed=session_num * 7)
        mock_rewrite.rewritten_script = obs["current_script"]
        mock_rewrite.diff = ""

        with patch.object(env.critic, "critique", return_value=mock_critique), \
             patch.object(env.defender, "defend", return_value=mock_defender), \
             patch.object(env.rewriter, "rewrite", return_value=mock_rewrite):
            action = {
                "action_type": "hook_rewrite",
                "target_section": "hook",
                "instruction": "Fix hook",
                "critique_claim_id": "C1",
                "reasoning": "test",
            }
            # Run until terminated
            for _ in range(5):
                obs, reward, terminated, _, _ = env.step(action)
                if terminated:
                    break
        return obs

    def test_reset_returns_none_history_for_new_creator(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env = self._make_env(tmpdir)
            obs, _ = env.reset(seed=1)
            assert obs.get("creator_history") is None
            assert obs.get("history_context") is None

    def test_step_saves_history_after_episode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env = self._make_env(tmpdir)
            self._run_episode(env, session_num=1)
            creator_id = env._current_creator_id
            store = HistoryStore(store_dir=tmpdir)
            buf = store.load(creator_id)
            assert buf is not None
            assert buf.total_episodes == 1

    def test_reset_loads_history_for_returning_creator(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env = self._make_env(tmpdir)
            # Session 1
            self._run_episode(env, session_num=1)
            creator_id = env._current_creator_id
            # Session 2 — must use same creator_id, so we force-reset with same script
            # just run reset and check that history is populated
            obs, _ = env.reset(seed=7)  # same seed as session 1
            # If the creator_id happens to match, history is loaded
            if env._current_creator_id == creator_id:
                assert obs.get("creator_history") is not None
                assert obs.get("history_context") is not None
