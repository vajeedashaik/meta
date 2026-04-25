"""
Tests for Phase 4 — Critic Escalation Engine.

Run: pytest viral_script_engine/tests/test_escalation.py -v
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

BASE_DIR = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_tracker(tmp_path):
    from viral_script_engine.escalation.difficulty_tracker import DifficultyTracker
    return DifficultyTracker(persistence_path=str(tmp_path / "tracker.json"))


@pytest.fixture
def dummy_challenge():
    from viral_script_engine.escalation.critic_escalation_engine import EscalatedChallenge
    return EscalatedChallenge(
        source_class="hook_weakness",
        script_text="This script has a subtle hook problem buried under misdirection.",
        region="Mumbai Gen Z",
        platform="Reels",
        dominant_flaw="hook_weakness",
        conflicting_flaw="pacing_issue",
        why_its_harder="Fixing hook early destroys pacing and lowers total reward.",
        optimal_action_order=["pacing_fix", "hook_rewrite"],
        trap_action="hook_rewrite",
    )


# ---------------------------------------------------------------------------
# Test 1: record_episode tracks consecutive resolutions correctly
# ---------------------------------------------------------------------------

def test_record_episode_tracks_consecutive(tmp_tracker):
    """Consecutive resolutions increment; a failure resets to 0."""
    tmp_tracker.record_episode("hook_weakness", 0.85, "ep1")
    assert tmp_tracker.records["hook_weakness"].consecutive_resolutions == 1

    tmp_tracker.record_episode("hook_weakness", 0.90, "ep2")
    assert tmp_tracker.records["hook_weakness"].consecutive_resolutions == 2

    tmp_tracker.record_episode("hook_weakness", 0.50, "ep3")
    assert tmp_tracker.records["hook_weakness"].consecutive_resolutions == 0


# ---------------------------------------------------------------------------
# Test 2: mastery triggers at exactly 3 consecutive resolutions, not 2
# ---------------------------------------------------------------------------

def test_mastery_triggers_at_3_not_2(tmp_tracker):
    """Mastery is set when consecutive_resolutions == mastery_threshold (3)."""
    tmp_tracker.record_episode("hook_weakness", 0.85, "ep1")
    assert not tmp_tracker.records["hook_weakness"].is_mastered

    tmp_tracker.record_episode("hook_weakness", 0.85, "ep2")
    assert not tmp_tracker.records["hook_weakness"].is_mastered

    tmp_tracker.record_episode("hook_weakness", 0.85, "ep3")
    assert tmp_tracker.records["hook_weakness"].is_mastered
    assert "hook_weakness" in tmp_tracker.get_mastered_classes()


# ---------------------------------------------------------------------------
# Test 3: mastery resets if agent fails after mastery achieved
# ---------------------------------------------------------------------------

def test_mastery_resets_on_failure(tmp_tracker):
    """A failure (r4 < 0.8) after mastery clears is_mastered."""
    for i in range(3):
        tmp_tracker.record_episode("hook_weakness", 0.9, f"ep{i}")
    assert tmp_tracker.records["hook_weakness"].is_mastered

    tmp_tracker.record_episode("hook_weakness", 0.3, "ep_fail")
    assert not tmp_tracker.records["hook_weakness"].is_mastered
    assert tmp_tracker.records["hook_weakness"].consecutive_resolutions == 0


# ---------------------------------------------------------------------------
# Test 4: CriticEscalationEngine.escalate() returns valid EscalatedChallenge
# ---------------------------------------------------------------------------

def test_escalation_engine_returns_valid_challenge():
    """escalate() returns an EscalatedChallenge with all required fields when LLM is mocked."""
    from viral_script_engine.escalation.critic_escalation_engine import CriticEscalationEngine

    mock_response = json.dumps({
        "script_text": "Today I'll teach you the one thing schools never told you about money.",
        "dominant_flaw": "hook_weakness",
        "conflicting_flaw": "pacing_issue",
        "why_its_harder": "Hook fix accelerates pacing and destroys retention.",
        "optimal_action_order": ["pacing_fix", "hook_rewrite"],
        "trap_action": "hook_rewrite",
    })

    engine = CriticEscalationEngine.__new__(CriticEscalationEngine)
    engine.escalated_classes = {}
    engine.llm = MagicMock()
    engine.llm.generate.return_value = mock_response

    challenge = engine.escalate(
        mastered_class="hook_weakness",
        original_script_example="Old script text here.",
        region="Mumbai Gen Z",
        platform="Reels",
    )

    assert challenge.source_class == "hook_weakness"
    assert challenge.script_text
    assert challenge.dominant_flaw == "hook_weakness"
    assert challenge.conflicting_flaw == "pacing_issue"
    assert challenge.difficulty_level == "self_generated"
    assert challenge.generated_at
    assert isinstance(challenge.optimal_action_order, list)
    assert challenge.trap_action


# ---------------------------------------------------------------------------
# Test 5: env.reset() uses escalated script when mastery is achieved
# ---------------------------------------------------------------------------

def test_env_reset_uses_escalated_script_on_mastery(tmp_path, dummy_challenge, monkeypatch):
    """When a class is mastered, env.reset() uses the escalated challenge script."""
    from viral_script_engine.environment.env import ViralScriptEnv
    from viral_script_engine.escalation.difficulty_tracker import DifficultyTracker
    from viral_script_engine.escalation.critic_escalation_engine import CriticEscalationEngine
    from viral_script_engine.rewards import r2_coherence, r5_defender_preservation
    from viral_script_engine.rewards.r2_coherence import CoherenceRewardResult
    from viral_script_engine.rewards.r5_defender_preservation import DefenderPreservationResult

    monkeypatch.setattr(
        r2_coherence.CoherenceReward, "score",
        lambda self, a, b: CoherenceRewardResult(score=0.75, raw_similarity=0.85, interpretation="good_coherence"),
    )
    monkeypatch.setattr(
        r5_defender_preservation.DefenderPreservationReward, "score",
        lambda self, d, s: DefenderPreservationResult(score=0.70, max_similarity=0.80, best_matching_sentence="[mock]"),
    )

    tracker = DifficultyTracker(persistence_path=str(tmp_path / "tracker.json"))
    for i in range(3):
        tracker.record_episode("hook_weakness", 0.9, f"ep{i}")
    assert tracker.records["hook_weakness"].is_mastered

    mock_engine = MagicMock(spec=CriticEscalationEngine)
    mock_engine.get_next_challenge.return_value = dummy_challenge

    env = ViralScriptEnv(
        scripts_path=str(BASE_DIR / "data" / "test_scripts" / "scripts.json"),
        cultural_kb_path=str(BASE_DIR / "data" / "cultural_kb.json"),
        max_steps=2,
        difficulty="easy",
        use_escalation=True,
        difficulty_tracker=tracker,
        escalation_engine=mock_engine,
    )

    obs, info = env.reset()

    assert info.get("escalation_used") is True
    assert obs["current_script"] == dummy_challenge.script_text
    assert obs["difficulty_level"] == "self_generated"


# ---------------------------------------------------------------------------
# Test 6: difficulty progression JSON is saved correctly
# ---------------------------------------------------------------------------

def test_progression_json_saved(tmp_path, tmp_tracker):
    """Progression JSON written by run_escalation_demo matches expected schema."""
    from viral_script_engine.escalation.critic_escalation_engine import CriticEscalationEngine

    engine = CriticEscalationEngine.__new__(CriticEscalationEngine)
    engine.escalated_classes = {}
    engine.llm = MagicMock()

    fake_episodes = [
        {"episode_num": i, "difficulty_level": "easy", "escalation_used": False,
         "total_reward": 0.5, "r4_score": 0.4, "steps": [], "tracker_summary": {}}
        for i in range(1, 6)
    ]

    from viral_script_engine.scripts.run_escalation_demo import _build_progression_report
    progression = _build_progression_report(fake_episodes, tmp_tracker, engine)

    out_path = tmp_path / "escalation_progression.json"
    with open(out_path, "w") as f:
        json.dump({"episodes": fake_episodes, "progression": progression}, f, indent=2)

    assert out_path.exists()
    with open(out_path) as f:
        loaded = json.load(f)

    assert "episodes" in loaded
    assert "progression" in loaded
    assert "mastery_events" in loaded["progression"]
    assert "total_escalated_challenges" in loaded["progression"]
