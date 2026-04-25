"""Phase 8 tests — Creator Persona Modelling."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from viral_script_engine.personas.creator_profile import CreatorProfile, CreatorTier, PostingFrequency
from viral_script_engine.personas.profile_generator import ProfileGenerator
from viral_script_engine.rewards.r8_persona_fit import PersonaFitReward
from viral_script_engine.environment.actions import ArbitratorAction, ActionType

KB_PATH = str(Path(__file__).parent.parent / "data" / "persona_advice_kb.json")


# ── ProfileGenerator ──────────────────────────────────────────────────────────

class TestProfileGenerator:
    def setup_method(self):
        self.gen = ProfileGenerator()

    def test_generate_beginner_within_range(self):
        p = self.gen.generate(CreatorTier.BEGINNER, "cooking", seed=1)
        assert 50 <= p.follower_count <= 999
        assert 0.08 <= p.avg_engagement_rate <= 0.15
        assert p.tier == CreatorTier.BEGINNER
        assert p.niche == "cooking"

    def test_generate_growing_within_range(self):
        p = self.gen.generate(CreatorTier.GROWING, "fitness", seed=2)
        assert 1000 <= p.follower_count <= 9999
        assert 0.04 <= p.avg_engagement_rate <= 0.08
        assert p.tier == CreatorTier.GROWING

    def test_generate_established_within_range(self):
        p = self.gen.generate(CreatorTier.ESTABLISHED, "tech reviews", seed=3)
        assert 10000 <= p.follower_count <= 99999
        assert 0.02 <= p.avg_engagement_rate <= 0.04
        assert p.tier == CreatorTier.ESTABLISHED

    def test_generate_verified_within_range(self):
        p = self.gen.generate(CreatorTier.VERIFIED, "comedy", seed=4)
        assert 100000 <= p.follower_count <= 2000000
        assert 0.01 <= p.avg_engagement_rate <= 0.02
        assert p.tier == CreatorTier.VERIFIED

    def test_generate_is_deterministic(self):
        p1 = self.gen.generate(CreatorTier.GROWING, "cooking", seed=42)
        p2 = self.gen.generate(CreatorTier.GROWING, "cooking", seed=42)
        assert p1.follower_count == p2.follower_count
        assert p1.avg_engagement_rate == p2.avg_engagement_rate
        assert p1.past_weak_points == p2.past_weak_points

    def test_generate_profile_has_weak_and_strong_points(self):
        p = self.gen.generate(CreatorTier.BEGINNER, "education", seed=7)
        assert 1 <= len(p.past_weak_points) <= 3
        assert 1 <= len(p.past_strong_points) <= 2
        overlap = set(p.past_weak_points) & set(p.past_strong_points)
        assert len(overlap) == 0, "Weak and strong points must not overlap"

    def test_generate_valid_pydantic_model(self):
        p = self.gen.generate(CreatorTier.ESTABLISHED, "personal finance", seed=10)
        assert isinstance(p, CreatorProfile)
        assert isinstance(p.posting_frequency, PostingFrequency)
        assert 0.0 <= p.avg_retention_rate <= 1.0

    def test_generate_batch_size(self):
        profiles = self.gen.generate_batch(20)
        assert len(profiles) == 20

    def test_generate_batch_tier_distribution(self):
        profiles = self.gen.generate_batch(200)
        tiers = [p.tier for p in profiles]
        beginner_ratio = tiers.count(CreatorTier.BEGINNER) / len(tiers)
        verified_ratio = tiers.count(CreatorTier.VERIFIED) / len(tiers)
        # beginner should be highest, verified should be lowest
        assert beginner_ratio > verified_ratio
        # beginner should be roughly 40% ± 15%
        assert 0.25 <= beginner_ratio <= 0.55

    def test_needs_fundamentals_property(self):
        beginner = self.gen.generate(CreatorTier.BEGINNER, "cooking", seed=1)
        verified = self.gen.generate(CreatorTier.VERIFIED, "cooking", seed=1)
        assert beginner.needs_fundamentals is True
        assert verified.needs_fundamentals is False

    def test_needs_refinement_property(self):
        established = self.gen.generate(CreatorTier.ESTABLISHED, "cooking", seed=1)
        beginner = self.gen.generate(CreatorTier.BEGINNER, "cooking", seed=1)
        assert established.needs_refinement is True
        assert beginner.needs_refinement is False


# ── PersonaFitReward ───────────────────────────────────────────────────────────

def _make_action(action_type: ActionType) -> ArbitratorAction:
    return ArbitratorAction(
        action_type=action_type,
        target_section="hook",
        instruction="Test instruction",
        critique_claim_id="C1",
        reasoning="Test reasoning",
    )


def _make_profile(tier: CreatorTier, weak_points=None) -> CreatorProfile:
    gen = ProfileGenerator()
    p = gen.generate(tier=tier, niche="fitness", seed=99)
    if weak_points is not None:
        p = p.model_copy(update={"past_weak_points": weak_points})
    return p


class TestPersonaFitReward:
    def setup_method(self):
        self.r8 = PersonaFitReward(kb_path=KB_PATH)

    def test_priority_action_scores_1(self):
        # hook_rewrite is priority for beginner
        action = _make_action(ActionType.HOOK_REWRITE)
        profile = _make_profile(CreatorTier.BEGINNER)
        result = self.r8.score(action, profile, addressed_critique_class="irrelevant")
        assert result.score == 1.0
        assert result.tier_match == "priority"
        assert result.is_forbidden is False

    def test_forbidden_action_scores_0(self):
        # hook_rewrite is forbidden for verified
        action = _make_action(ActionType.HOOK_REWRITE)
        profile = _make_profile(CreatorTier.VERIFIED)
        result = self.r8.score(action, profile, addressed_critique_class="hook_weakness")
        assert result.score == 0.0
        assert result.is_forbidden is True

    def test_deprioritised_action_scores_low(self):
        # cultural_ref_sub is deprioritised for beginner
        # pass explicit weak_points that exclude cultural_mismatch to avoid the +0.1 bonus
        action = _make_action(ActionType.CULTURAL_REF_SUB)
        profile = _make_profile(CreatorTier.BEGINNER, weak_points=["hook_weakness"])
        result = self.r8.score(action, profile, addressed_critique_class="cultural_mismatch")
        assert result.score == pytest.approx(0.2, abs=0.01)
        assert result.tier_match == "deprioritised"

    def test_neutral_action_scores_mid(self):
        # cta_placement is neutral for growing tier:
        #   priority=[hook_rewrite, section_reorder], deprioritised=[cultural_ref_sub], forbidden=[]
        # pass weak_points that exclude cta_buried to avoid the +0.1 bonus
        action = _make_action(ActionType.CTA_PLACEMENT)
        profile = _make_profile(CreatorTier.GROWING, weak_points=["hook_weakness"])
        result = self.r8.score(action, profile, addressed_critique_class="cta_buried")
        assert result.score == pytest.approx(0.5, abs=0.01)
        assert result.tier_match == "neutral"

    def test_recurring_weakness_bonus_applied(self):
        # beginner, hook_rewrite (priority=1.0) + hook_weakness in weak points
        action = _make_action(ActionType.HOOK_REWRITE)
        profile = _make_profile(CreatorTier.BEGINNER, weak_points=["hook_weakness", "cta_buried"])
        result = self.r8.score(action, profile, addressed_critique_class="hook_weakness")
        assert result.recurring_weakness_bonus == pytest.approx(0.1)
        assert result.score == pytest.approx(1.0)  # capped at 1.0

    def test_recurring_weakness_bonus_not_applied_when_not_matching(self):
        action = _make_action(ActionType.HOOK_REWRITE)
        profile = _make_profile(CreatorTier.BEGINNER, weak_points=["pacing_issue"])
        result = self.r8.score(action, profile, addressed_critique_class="hook_weakness")
        assert result.recurring_weakness_bonus == 0.0
        assert result.score == pytest.approx(1.0)

    def test_score_capped_at_1(self):
        # priority (1.0) + bonus (0.1) should be capped at 1.0
        action = _make_action(ActionType.HOOK_REWRITE)
        profile = _make_profile(CreatorTier.BEGINNER, weak_points=["hook_weakness"])
        result = self.r8.score(action, profile, addressed_critique_class="hook_weakness")
        assert result.score <= 1.0

    def test_result_has_explanation(self):
        action = _make_action(ActionType.SECTION_REORDER)
        profile = _make_profile(CreatorTier.GROWING)
        result = self.r8.score(action, profile, addressed_critique_class="pacing_issue")
        assert isinstance(result.explanation, str)
        assert len(result.explanation) > 0


import json as _json

_MOCK_CRITIC = _json.dumps({
    "claims": [
        {
            "claim_id": "C1",
            "critique_class": "hook_weakness",
            "claim_text": "Weak hook.",
            "timestamp_range": "0:00-0:03",
            "evidence": "generic opener",
            "is_falsifiable": True,
            "severity": "high",
        }
    ],
    "overall_severity": "high",
})

_MOCK_DEFENDER = _json.dumps({
    "core_strength": "Strong regional authenticity",
    "core_strength_quote": "The hook draws viewers immediately",
    "defense_argument": "Regional voice is valuable",
    "flagged_critic_claims": [],
    "regional_voice_elements": ["local phrase"],
})

_MOCK_REWRITER = _json.dumps({
    "rewritten_script": "Better script content here.",
    "changes_made": ["improved hook"],
})


def _multi_mock(sys_prompt, usr_prompt, **kw):
    if "core_strength" in sys_prompt or "defender" in sys_prompt.lower():
        return _MOCK_DEFENDER
    if "rewriter" in sys_prompt.lower() or "rewrite" in sys_prompt.lower()[:50]:
        return _MOCK_REWRITER
    return _MOCK_CRITIC


# ── Environment integration ────────────────────────────────────────────────────

class TestEnvironmentIntegration:
    """Tests that env.reset() and step() produce correct profile and R8."""

    def _make_env(self, difficulty="medium"):
        from viral_script_engine.environment.env import ViralScriptEnv
        base = Path(__file__).parent.parent
        return ViralScriptEnv(
            scripts_path=str(base / "data" / "test_scripts" / "scripts.json"),
            cultural_kb_path=str(base / "data" / "cultural_kb.json"),
            max_steps=2,
            difficulty=difficulty,
            use_anti_gaming=False,
            use_escalation=False,
        )

    def test_reset_returns_creator_profile(self):
        env = self._make_env()
        obs, _ = env.reset(seed=1)
        assert "creator_profile" in obs
        assert obs["creator_profile"] is not None
        assert "tier" in obs["creator_profile"]

    def test_profile_tier_matches_difficulty_easy(self):
        env = self._make_env(difficulty="easy")
        obs, _ = env.reset(seed=1)
        tier = obs["creator_profile"]["tier"]
        assert tier in ["beginner", "growing"]

    def test_profile_tier_matches_difficulty_hard(self):
        env = self._make_env(difficulty="hard")
        obs, _ = env.reset(seed=1)
        tier = obs["creator_profile"]["tier"]
        assert tier in ["established", "verified"]

    def test_step_returns_r8_in_reward_components(self, monkeypatch):
        monkeypatch.setattr(
            "viral_script_engine.agents.llm_backend.LLMBackend.generate",
            lambda self, sys_prompt, usr_prompt, **kw: _multi_mock(sys_prompt, usr_prompt, **kw),
        )
        env = self._make_env()
        env.reset(seed=5)
        action = {
            "action_type": "hook_rewrite",
            "target_section": "hook",
            "instruction": "Rewrite the hook.",
            "critique_claim_id": "C1",
            "reasoning": "Testing R8",
        }
        obs, reward, done, trunc, info = env.step(action)
        rc = info["reward_components"]
        assert "r8_persona_fit" in rc

    def test_observation_includes_profile_dict(self):
        env = self._make_env()
        obs, _ = env.reset(seed=3)
        profile = obs["creator_profile"]
        assert isinstance(profile["follower_count"], int)
        assert isinstance(profile["avg_engagement_rate"], float)
        assert isinstance(profile["past_weak_points"], list)

    def test_prompt_template_includes_profile_fields(self):
        from viral_script_engine.training.rollout_function import _format_observation_prompt
        obs = {
            "current_script": "Test script",
            "region": "Mumbai",
            "platform": "Reels",
            "niche": "fitness",
            "reward_components": {"r1_hook_strength": 0.5, "r2_coherence": 0.6},
            "debate_history": [],
            "creator_profile": {
                "tier": "growing",
                "follower_count": 4200,
                "posting_frequency": "regular",
                "past_weak_points": ["hook_weakness", "cta_buried"],
                "voice_descriptors": ["direct", "Hinglish"],
                "niche_maturity": "established_in_niche",
            },
        }
        prompt = _format_observation_prompt(obs, step_num=1, max_steps=3)
        assert "CREATOR PROFILE" in prompt
        assert "growing" in prompt
        assert "4200" in prompt
        assert "hook_weakness" in prompt
