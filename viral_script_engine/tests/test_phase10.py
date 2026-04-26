"""Phase 10 tests — A/B Testing Environment Layer."""
import math
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from viral_script_engine.environment.trajectory import Trajectory, TrajectoryType
from viral_script_engine.rewards.contrastive_reward import ContrastiveReward, ContrastiveRewardResult

_SCRIPTS_PATH = str(
    Path(__file__).parent.parent / "data" / "test_scripts" / "scripts.json"
)
_CULTURAL_KB_PATH = str(
    Path(__file__).parent.parent / "data" / "cultural_kb.json"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_claim(claim_id: str, severity: str, critique_class: str) -> MagicMock:
    c = MagicMock()
    c.claim_id = claim_id
    c.severity = severity
    c.critique_class = critique_class
    c.claim_text = f"Test claim {claim_id}"
    return c


def _make_defender(core_quote: str, flagged: list = None) -> MagicMock:
    d = MagicMock()
    d.core_strength_quote = core_quote
    d.flagged_critic_claims = flagged or []
    return d


def _make_trajectory(
    traj_type: str,
    cumulative: float,
    script: str = "Test script body content here.",
) -> Trajectory:
    return Trajectory(
        trajectory_id=f"test_{traj_type}",
        trajectory_type=traj_type,
        initial_script=script,
        current_script=script,
        cumulative_reward=cumulative,
    )


# ---------------------------------------------------------------------------
# Trajectory: forced first action — CRITIC_FIRST
# ---------------------------------------------------------------------------

class TestTrajectoryForcedActionCriticFirst:
    def setup_method(self):
        self.traj = _make_trajectory(TrajectoryType.CRITIC_FIRST, 0.0)

    def test_picks_highest_severity_claim(self):
        claims = [
            _make_claim("C1", "low", "pacing_issue"),
            _make_claim("C2", "high", "hook_weakness"),
            _make_claim("C3", "medium", "cta_buried"),
        ]
        action = self.traj.get_forced_first_action(claims, None)
        # highest severity is C2 (high, hook_weakness → hook_rewrite)
        assert action["action_type"] == "hook_rewrite"
        assert action["critique_claim_id"] == "C2"

    def test_maps_cta_buried_to_cta_placement(self):
        claims = [_make_claim("C1", "high", "cta_buried")]
        action = self.traj.get_forced_first_action(claims, None)
        assert action["action_type"] == "cta_placement"
        assert action["target_section"] == "cta"

    def test_maps_cultural_mismatch_to_cultural_ref_sub(self):
        claims = [_make_claim("C1", "high", "cultural_mismatch")]
        action = self.traj.get_forced_first_action(claims, None)
        assert action["action_type"] == "cultural_ref_sub"

    def test_fallback_when_no_claims(self):
        action = self.traj.get_forced_first_action([], None)
        assert action["action_type"] == "hook_rewrite"
        assert "CRITIC_FIRST" in action["reasoning"] or action["reasoning"]

    def test_reasoning_mentions_critic_first(self):
        claims = [_make_claim("C1", "high", "hook_weakness")]
        action = self.traj.get_forced_first_action(claims, None)
        assert "CRITIC_FIRST" in action["reasoning"]


# ---------------------------------------------------------------------------
# Trajectory: forced first action — DEFENDER_FIRST
# ---------------------------------------------------------------------------

class TestTrajectoryForcedActionDefenderFirst:
    def test_picks_cta_when_core_strength_in_hook(self):
        # Script starts with the core quote → hook is precious
        script = "Why does your phone battery lie? Charge to eighty. Never below twenty."
        traj = _make_trajectory(TrajectoryType.DEFENDER_FIRST, 0.0, script=script)
        defender = _make_defender(core_quote="Why does your phone battery lie?")
        claims = [_make_claim("C1", "high", "hook_weakness")]

        action = traj.get_forced_first_action(claims, defender)
        assert action["action_type"] == "cta_placement", (
            f"Expected cta_placement when core strength is in hook, got {action['action_type']}"
        )

    def test_picks_hook_rewrite_when_core_strength_in_body(self):
        # Script hook is entirely generic; core quote only appears after the first 100 chars
        filler = "Stop wasting your money on things that do not matter at all. " * 2  # >100 chars
        core = "UNIQUE_CORE_PHRASE_XYZ"
        script = filler + core
        traj = _make_trajectory(TrajectoryType.DEFENDER_FIRST, 0.0, script=script)
        # Core quote appears after position 100 — NOT in hook
        defender = _make_defender(core_quote=core)
        claims = [_make_claim("C1", "high", "hook_weakness")]

        action = traj.get_forced_first_action(claims, defender)
        assert action["action_type"] == "hook_rewrite", (
            f"Expected hook_rewrite when core is NOT in hook, got {action['action_type']}"
        )

    def test_reasoning_mentions_defender_first(self):
        traj = _make_trajectory(TrajectoryType.DEFENDER_FIRST, 0.0)
        action = traj.get_forced_first_action([], None)
        assert "DEFENDER_FIRST" in action["reasoning"]

    def test_skips_flagged_claims_in_defender_first(self):
        script = "Body content only. No hook magic here at all whatsoever for testing purposes."
        traj = _make_trajectory(TrajectoryType.DEFENDER_FIRST, 0.0, script=script)
        defender = _make_defender(
            core_quote="definitely not in the hook portion of this script",
            flagged=["C1"],
        )
        claims = [
            _make_claim("C1", "high", "hook_weakness"),
            _make_claim("C2", "medium", "pacing_issue"),
        ]
        action = traj.get_forced_first_action(claims, defender)
        # C1 is flagged, so should pick C2
        assert action["critique_claim_id"] == "C2"


# ---------------------------------------------------------------------------
# ContrastiveReward
# ---------------------------------------------------------------------------

class TestContrastiveReward:
    def setup_method(self):
        self.cr = ContrastiveReward()

    def test_delta_computed_correctly(self):
        traj_a = _make_trajectory(TrajectoryType.CRITIC_FIRST, 0.7)
        traj_b = _make_trajectory(TrajectoryType.DEFENDER_FIRST, 0.5)
        result = self.cr.compute(traj_a, traj_b)
        assert abs(result.delta - 0.2) < 1e-9

    def test_winning_trajectory_is_a_when_a_higher(self):
        traj_a = _make_trajectory(TrajectoryType.CRITIC_FIRST, 0.8)
        traj_b = _make_trajectory(TrajectoryType.DEFENDER_FIRST, 0.5)
        result = self.cr.compute(traj_a, traj_b)
        assert result.winning_trajectory == "A"
        assert result.winning_trajectory_type == TrajectoryType.CRITIC_FIRST

    def test_winning_trajectory_is_b_when_b_higher(self):
        traj_a = _make_trajectory(TrajectoryType.CRITIC_FIRST, 0.4)
        traj_b = _make_trajectory(TrajectoryType.DEFENDER_FIRST, 0.7)
        result = self.cr.compute(traj_a, traj_b)
        assert result.winning_trajectory == "B"
        assert result.winning_trajectory_type == TrajectoryType.DEFENDER_FIRST

    def test_tie_when_delta_is_zero(self):
        traj_a = _make_trajectory(TrajectoryType.CRITIC_FIRST, 0.6)
        traj_b = _make_trajectory(TrajectoryType.DEFENDER_FIRST, 0.6)
        result = self.cr.compute(traj_a, traj_b)
        assert result.winning_trajectory == "tie"

    def test_contrast_bonus_near_zero_when_delta_small(self):
        # delta = 0.01 → tanh(0.01 * 3) * 0.2 ≈ 0.006 — near zero
        traj_a = _make_trajectory(TrajectoryType.CRITIC_FIRST, 0.51)
        traj_b = _make_trajectory(TrajectoryType.DEFENDER_FIRST, 0.50)
        result = self.cr.compute(traj_a, traj_b)
        assert abs(result.contrast_bonus) < 0.02, (
            f"contrast_bonus should be near 0 for delta=0.01, got {result.contrast_bonus}"
        )

    def test_contrast_bonus_positive_when_delta_large(self):
        # delta = 0.3 → tanh(0.9) * 0.2 ≈ 0.156 — clearly positive
        traj_a = _make_trajectory(TrajectoryType.CRITIC_FIRST, 0.7)
        traj_b = _make_trajectory(TrajectoryType.DEFENDER_FIRST, 0.4)
        result = self.cr.compute(traj_a, traj_b)
        assert result.contrast_bonus > 0.1, (
            f"contrast_bonus should be > 0.1 for delta=0.3, got {result.contrast_bonus}"
        )

    def test_final_reward_clipped_to_0_1_upper(self):
        # Very high cumulative rewards should still clip to 1.0
        traj_a = _make_trajectory(TrajectoryType.CRITIC_FIRST, 5.0)
        traj_b = _make_trajectory(TrajectoryType.DEFENDER_FIRST, 0.1)
        result = self.cr.compute(traj_a, traj_b)
        assert result.final_reward <= 1.0

    def test_final_reward_clipped_to_0_1_lower(self):
        # Negative cumulative rewards should clip to 0.0
        traj_a = _make_trajectory(TrajectoryType.CRITIC_FIRST, -1.0)
        traj_b = _make_trajectory(TrajectoryType.DEFENDER_FIRST, -2.0)
        result = self.cr.compute(traj_a, traj_b)
        assert result.final_reward >= 0.0

    def test_final_reward_always_in_0_1(self):
        for cum_a, cum_b in [(0.3, 0.3), (0.9, 0.1), (0.0, 0.0), (0.5, 0.5), (1.0, 0.0)]:
            traj_a = _make_trajectory(TrajectoryType.CRITIC_FIRST, cum_a)
            traj_b = _make_trajectory(TrajectoryType.DEFENDER_FIRST, cum_b)
            result = self.cr.compute(traj_a, traj_b)
            assert 0.0 <= result.final_reward <= 1.0, (
                f"final_reward={result.final_reward} out of [0,1] for "
                f"cum_a={cum_a}, cum_b={cum_b}"
            )

    def test_base_reward_is_max(self):
        traj_a = _make_trajectory(TrajectoryType.CRITIC_FIRST, 0.7)
        traj_b = _make_trajectory(TrajectoryType.DEFENDER_FIRST, 0.5)
        result = self.cr.compute(traj_a, traj_b)
        assert abs(result.base_reward - 0.7) < 1e-9

    def test_result_is_contrastive_reward_result_instance(self):
        traj_a = _make_trajectory(TrajectoryType.CRITIC_FIRST, 0.6)
        traj_b = _make_trajectory(TrajectoryType.DEFENDER_FIRST, 0.4)
        result = self.cr.compute(traj_a, traj_b)
        assert isinstance(result, ContrastiveRewardResult)


# ---------------------------------------------------------------------------
# ABScriptEnv — integration tests using mocked env.step() and reset()
# ---------------------------------------------------------------------------

def _fake_obs(script: str = "Test script.", reward: float = 0.5) -> dict:
    return {
        "current_script": script,
        "original_script": script,
        "region": "pan_india_english",
        "platform": "Reels",
        "niche": "personal finance",
        "step_num": 1,
        "max_steps": 3,
        "debate_history": [],
        "reward_components": {"r1_hook_strength": reward, "total": reward},
        "difficulty_level": "easy",
        "episode_id": "ep_test",
        "current_moderation_flags": [],
        "current_originality_flags": [],
        "creator_profile": None,
    }


def _fake_step_result(script: str = "Test script.", reward: float = 0.5, done: bool = False):
    obs = _fake_obs(script, reward)
    info = {"reward_components": {"r1_hook_strength": reward, "total": reward}}
    return obs, reward, done, False, info


def _make_real_critique(claim_id="C1", severity="high", critique_class="hook_weakness"):
    """Return a MagicMock with real CritiqueClaim objects so pydantic validation passes."""
    from viral_script_engine.agents.critic import CritiqueClaim, CritiqueOutput
    claim = CritiqueClaim(
        claim_id=claim_id,
        critique_class=critique_class,
        claim_text=f"Test {critique_class} claim",
        timestamp_range="0:00-0:05",
        evidence="test evidence here",
        is_falsifiable=True,
        severity=severity,
    )
    mock_crit = MagicMock()
    mock_crit.claims = [claim]
    mock_crit.overall_severity = severity
    return mock_crit


def _make_real_defender(core_quote="hook content here"):
    from viral_script_engine.agents.defender import DefenderOutput
    return DefenderOutput(
        core_strength="Strong hook",
        core_strength_quote=core_quote,
        defense_argument="Preserve this element.",
        flagged_critic_claims=[],
        regional_voice_elements=[],
    )


class TestABScriptEnvMocked:
    """Test ABScriptEnv behaviour with env.step() mocked at the env level."""

    def _make_ab_env(self):
        from viral_script_engine.environment.ab_env import ABScriptEnv
        return ABScriptEnv(
            scripts_path=_SCRIPTS_PATH,
            cultural_kb_path=_CULTURAL_KB_PATH,
            max_steps=3,
            difficulty="easy",
        )

    def _reset_with_mocks(self, ab_env, core_quote="body content deep here", seed=42):
        """
        Reset ab_env with mocked critic, defender, and step calls.
        Uses real CritiqueClaim/DefenderOutput to pass pydantic validation.
        Returns the state dict.
        """
        mock_critique = _make_real_critique("C1", "high", "hook_weakness")
        mock_defender = _make_real_defender(core_quote)

        with patch.object(ab_env.env_a.critic, "critique", return_value=mock_critique), \
             patch.object(ab_env.env_a.defender, "defend", return_value=mock_defender), \
             patch.object(ab_env.env_b.step, "__call__", side_effect=None) if False else \
             patch.object(ab_env.env_a, "step",
                          side_effect=lambda action, **kw: _fake_step_result("Script A.", 0.65)), \
             patch.object(ab_env.env_b, "step",
                          side_effect=lambda action, **kw: _fake_step_result("Script B.", 0.55)):
            state = ab_env.reset(seed=seed)
        return state

    def test_reset_gives_both_trajectory_states(self):
        ab_env = self._make_ab_env()
        state = self._reset_with_mocks(ab_env)

        assert "trajectory_a" in state
        assert "trajectory_b" in state
        assert "delta" in state
        assert "leading_trajectory" in state
        assert "episode_id" in state

    def test_both_envs_start_from_same_script(self):
        ab_env = self._make_ab_env()
        self._reset_with_mocks(ab_env, seed=42)

        # Both trajectories must share the same initial_script (same reset seed)
        assert ab_env._traj_a.initial_script == ab_env._traj_b.initial_script

    def test_step_1_forced_actions_differ(self):
        """
        Traj A (critic_first, hook_weakness claim) → hook_rewrite.
        Traj B (defender_first, core in hook) → cta_placement.
        """
        import json as _json
        scripts = _json.loads(open(_SCRIPTS_PATH).read())
        easy_script = next(s for s in scripts if s["script_id"] == "S01")
        # Use first 30 chars of the real script as the "core quote" so it appears in the hook
        hook_text = easy_script["script_text"][:30]

        ab_env = self._make_ab_env()
        mock_critique = _make_real_critique("C1", "high", "hook_weakness")
        mock_defender = _make_real_defender(core_quote=hook_text)

        with patch.object(ab_env.env_a.critic, "critique", return_value=mock_critique), \
             patch.object(ab_env.env_a.defender, "defend", return_value=mock_defender), \
             patch.object(ab_env.env_a, "step",
                          side_effect=lambda action, **kw: _fake_step_result()), \
             patch.object(ab_env.env_b, "step",
                          side_effect=lambda action, **kw: _fake_step_result()):
            ab_env.reset(seed=42)

        action_a = ab_env._forced_action_a.get("action_type")
        action_b = ab_env._forced_action_b.get("action_type")
        assert action_a == "hook_rewrite", (
            f"CRITIC_FIRST: expected hook_rewrite, got {action_a}"
        )
        assert action_b == "cta_placement", (
            f"DEFENDER_FIRST (core in hook): expected cta_placement, got {action_b}"
        )

    def test_step_applies_same_action_to_both(self):
        ab_env = self._make_ab_env()
        self._reset_with_mocks(ab_env)

        step_calls_a: list = []
        step_calls_b: list = []

        def track_a(action, **kw):
            step_calls_a.append(action)
            return _fake_step_result("A after free step", 0.7, done=True)

        def track_b(action, **kw):
            step_calls_b.append(action)
            return _fake_step_result("B after free step", 0.6, done=True)

        free_action = {
            "action_type": "cta_placement",
            "target_section": "cta",
            "instruction": "Move CTA to end.",
            "critique_claim_id": "C1",
            "reasoning": "test",
        }
        with patch.object(ab_env.env_a, "step", side_effect=track_a), \
             patch.object(ab_env.env_b, "step", side_effect=track_b):
            ab_env.step(free_action)

        assert len(step_calls_a) == 1
        assert len(step_calls_b) == 1
        assert step_calls_a[0]["action_type"] == step_calls_b[0]["action_type"] == "cta_placement"

    def test_state_returns_correct_delta(self):
        ab_env = self._make_ab_env()
        self._reset_with_mocks(ab_env)

        # Manually set cumulative rewards to known values
        ab_env._traj_a.cumulative_reward = 0.7
        ab_env._traj_b.cumulative_reward = 0.5

        state = ab_env.state()
        assert abs(state["delta"] - 0.2) < 1e-9
        assert state["leading_trajectory"] == "A"
        assert "trajectory_a" in state
        assert "trajectory_b" in state
