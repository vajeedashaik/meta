import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from viral_script_engine.agents.critic import CritiqueOutput, CritiqueClaim
from viral_script_engine.agents.rewriter import RewriteResult
from viral_script_engine.environment.actions import ActionType, ArbitratorAction

FIXTURE_DIR = Path(__file__).parent.parent / "data" / "golden_fixtures"
SCRIPTS_PATH = str(Path(__file__).parent.parent / "data" / "test_scripts" / "scripts.json")


def load_fixture(script_id: str) -> dict:
    with open(FIXTURE_DIR / f"fixture_{script_id}.json") as f:
        return json.load(f)


def make_mock_critique() -> CritiqueOutput:
    fixture = load_fixture("S01")
    claims = [CritiqueClaim(**c) for c in fixture["critique"]["claims"]]
    return CritiqueOutput(
        claims=claims,
        overall_severity=fixture["critique"]["overall_severity"],
        raw_response=fixture["critique"]["raw_response"],
    )


def make_mock_rewrite(current_script: str, action: ArbitratorAction) -> RewriteResult:
    return RewriteResult(
        rewritten_script=current_script + " [REWRITTEN]",
        diff="@@ diff @@",
        word_count_delta=1,
    )


SAMPLE_ACTION = {
    "action_type": ActionType.HOOK_REWRITE.value,
    "target_section": "hook",
    "instruction": "Make the hook more attention-grabbing with a specific number.",
    "critique_claim_id": "C1",
    "reasoning": "Hook is weak per C1",
}


@pytest.fixture
def env():
    with (
        patch("viral_script_engine.environment.env.CriticAgent") as mock_critic_cls,
        patch("viral_script_engine.environment.env.RewriterAgent") as mock_rewriter_cls,
        patch("viral_script_engine.environment.env.DefenderAgent") as mock_defender_cls,
        patch("viral_script_engine.environment.env.CulturalAlignmentReward") as mock_r3_cls,
        patch("viral_script_engine.environment.env.DebateResolutionReward") as mock_r4_cls,
        patch("viral_script_engine.environment.env.DefenderPreservationReward") as mock_r5_cls,
    ):
        mock_critic = MagicMock()
        mock_critic.critique.return_value = make_mock_critique()
        mock_critic_cls.return_value = mock_critic

        mock_rewriter = MagicMock()
        mock_rewriter.rewrite.side_effect = make_mock_rewrite
        mock_rewriter_cls.return_value = mock_rewriter

        mock_defender = MagicMock()
        from viral_script_engine.agents.defender import DefenderOutput
        mock_defender.defend.return_value = DefenderOutput(
            core_strength="strong hook",
            core_strength_quote="test quote",
            defense_argument="preserve it",
            flagged_critic_claims=[],
            regional_voice_elements=[],
        )
        mock_defender_cls.return_value = mock_defender

        mock_r3 = MagicMock()
        mock_r3.score.return_value = MagicMock(score=0.6)
        mock_r3_cls.return_value = mock_r3

        mock_r4 = MagicMock()
        from viral_script_engine.rewards.r4_debate_resolution import DebateResolutionResult
        mock_r4.score.return_value = DebateResolutionResult(
            score=0.8,
            resolution_status="resolved",
            original_claim_id="C1",
            original_claim_class="hook_weakness",
            new_claims_count=2,
        )
        mock_r4_cls.return_value = mock_r4

        mock_r5 = MagicMock()
        from viral_script_engine.rewards.r5_defender_preservation import DefenderPreservationResult
        mock_r5.score.return_value = DefenderPreservationResult(
            score=0.9, max_similarity=0.9, best_matching_sentence="test quote"
        )
        mock_r5_cls.return_value = mock_r5

        from viral_script_engine.environment.env import ViralScriptEnv
        yield ViralScriptEnv(scripts_path=SCRIPTS_PATH, max_steps=5, difficulty="easy", use_escalation=False)


def test_reset_returns_valid_observation(env):
    obs, info = env.reset(seed=42)
    assert "current_script" in obs
    assert obs["step_num"] == 0
    assert obs["max_steps"] == 5
    assert obs["reward_components"]["r1_hook_strength"] is not None
    assert obs["reward_components"]["r2_coherence"] is not None


def test_step_completes_without_error(env):
    env.reset(seed=42)
    obs, reward, terminated, truncated, info = env.step(SAMPLE_ACTION)
    assert isinstance(reward, float)
    assert "reward_components" in info


def test_step_increments_step_num(env):
    env.reset(seed=42)
    obs, *_ = env.step(SAMPLE_ACTION)
    assert obs["step_num"] == 1
    obs, *_ = env.step(SAMPLE_ACTION)
    assert obs["step_num"] == 2


def test_anti_gaming_penalty_fires_on_repeated_action(env):
    env.reset(seed=42)
    for _ in range(3):
        obs, reward, _, _, info = env.step(SAMPLE_ACTION)
    assert info["anti_gaming_triggered"]


def test_episode_terminates_at_max_steps(env):
    env.reset(seed=42)
    terminated = False
    for _ in range(5):
        obs, reward, terminated, truncated, info = env.step(SAMPLE_ACTION)
    assert terminated


def test_reward_clipped_to_0_1(env):
    env.reset(seed=42)
    _, reward, _, _, _ = env.step(SAMPLE_ACTION)
    assert 0.0 <= reward <= 1.0
