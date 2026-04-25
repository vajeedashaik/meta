"""Phase 6 tests: ModerationAgent, OriginalityAgent, R6/R7 rewards, aggregator, env.step()."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from viral_script_engine.agents.moderation_agent import ModerationAgent, ModerationOutput
from viral_script_engine.agents.originality_agent import OriginalityAgent, OriginalityOutput
from viral_script_engine.rewards.r6_safety import SafetyReward
from viral_script_engine.rewards.r7_originality import OriginalityReward
from viral_script_engine.rewards.reward_aggregator import RewardAggregator
from viral_script_engine.environment.observations import RewardComponents

BASE_DIR = Path(__file__).parent.parent


@pytest.fixture
def moderation_agent():
    return ModerationAgent(kb_path=str(BASE_DIR / "data" / "shadowban_triggers.json"))


@pytest.fixture
def originality_agent():
    return OriginalityAgent(templates_path=str(BASE_DIR / "data" / "viral_templates.json"))


@pytest.fixture
def r6():
    return SafetyReward()


@pytest.fixture
def r7():
    return OriginalityReward()


# ── ModerationAgent ────────────────────────────────────────────────────────────

class TestModerationAgent:
    def test_flags_high_severity_health_claim(self, moderation_agent):
        script = (
            "Doctors don't want you to know this miracle remedy. "
            "It is a guaranteed weight loss solution that cures everything. "
            "Get started today."
        )
        result = moderation_agent.check(script)
        assert result.total_flags > 0
        severities = [f.severity for f in result.flags]
        assert "high" in severities

    def test_flags_policy_violation(self, moderation_agent):
        script = (
            "Want to grow your audience fast? Buy followers today. "
            "Make $5000 in 30 days guaranteed — it's the easiest passive income. "
            "Get rich quick with our proven method."
        )
        result = moderation_agent.check(script)
        assert result.total_flags > 0
        categories = [f.category for f in result.flags]
        assert "policy_violation" in categories

    def test_flags_engagement_bait(self, moderation_agent):
        script = (
            "Here's something nobody talks about in fitness. "
            "These 3 exercises changed my life completely. "
            "Comment if you agree and tag 3 friends who need this."
        )
        result = moderation_agent.check(script)
        assert result.total_flags > 0

    def test_clean_script_is_safe(self, moderation_agent):
        script = (
            "I tested three different morning routines for 30 days each. "
            "The data surprised me — the simplest one produced the best results. "
            "Here's what I found and what I now do every day."
        )
        result = moderation_agent.check(script)
        assert result.is_safe is True
        assert result.overall_risk == "safe"

    def test_high_severity_flag_sets_is_safe_false(self, moderation_agent):
        script = (
            "This miracle remedy cures cancer permanently. "
            "Big pharma is hiding this from you. "
            "Share before it gets taken down."
        )
        result = moderation_agent.check(script)
        assert result.is_safe is False


# ── SafetyReward ───────────────────────────────────────────────────────────────

class TestSafetyReward:
    def test_zero_score_on_high_severity(self, moderation_agent, r6):
        script = (
            "This miracle remedy cures all diseases overnight. "
            "Buy followers now to grow faster. "
            "Make $10,000 in 30 days guaranteed."
        )
        mod_out = moderation_agent.check(script)
        result = r6.score(mod_out)
        assert result.score == 0.0

    def test_full_score_on_clean_script(self, moderation_agent, r6):
        script = (
            "I spent 6 months studying sleep science. "
            "These 3 evidence-based habits improved my sleep quality measurably. "
            "Start with the simplest one first."
        )
        mod_out = moderation_agent.check(script)
        result = r6.score(mod_out)
        assert result.score == 1.0

    def test_medium_score_on_medium_severity(self, moderation_agent, r6):
        script = (
            "This app is a must-have. "
            "Watch the full movie version for free on our site. "
            "Click the link below for the download."
        )
        mod_out = moderation_agent.check(script)
        result = r6.score(mod_out)
        # medium or high severity — score should be <= 0.5
        assert result.score <= 0.5


# ── OriginalityAgent ───────────────────────────────────────────────────────────

class TestOriginalityAgent:
    def test_detects_overused_hook(self, originality_agent):
        script = (
            "Nobody talks about this but your morning routine is wrong. "
            "Here are three things I wish I knew before starting. "
            "Follow for more tips."
        )
        result = originality_agent.check(script)
        assert len(result.flags) > 0
        template_types = [f.template_type for f in result.flags]
        assert any(t in ("overused_hook", "overused_cta") for t in template_types)

    def test_unique_script_scores_high(self, originality_agent):
        script = (
            "In 2019, the average Indian millennial checked their phone 94 times a day. "
            "I tracked my own usage for a month and found a pattern nobody warned me about. "
            "The solution had nothing to do with willpower."
        )
        result = originality_agent.check(script)
        assert result.originality_score >= 0.8

    def test_template_clone_is_generic(self, originality_agent):
        script = (
            "Nobody talks about this but you have been doing it wrong your whole life. "
            "Stop doing this immediately and save this for later. "
            "Follow for more and share with someone who needs this."
        )
        result = originality_agent.check(script)
        assert result.is_generic is True or result.originality_score < 0.6


# ── OriginalityReward ──────────────────────────────────────────────────────────

class TestOriginalityReward:
    def test_zero_score_on_template_clone(self, originality_agent, r7):
        script = (
            "Nobody talks about this but you have been doing it wrong your whole life. "
            "Stop doing this immediately and save this for later. "
            "Follow for more and share with someone who needs this."
        )
        orig_out = originality_agent.check(script)
        # Force a low originality_score scenario
        from viral_script_engine.agents.originality_agent import OriginalityOutput
        low_out = OriginalityOutput(
            flags=orig_out.flags,
            originality_score=0.2,
            is_generic=True,
            unique_elements=[],
        )
        result = r7.score(low_out)
        assert result.score == 0.0

    def test_full_score_on_high_originality(self, originality_agent, r7):
        from viral_script_engine.agents.originality_agent import OriginalityOutput
        high_out = OriginalityOutput(
            flags=[],
            originality_score=0.95,
            is_generic=False,
            unique_elements=["unique sentence 1", "unique sentence 2"],
        )
        result = r7.score(high_out)
        assert result.score == 1.0


# ── RewardAggregator with R6/R7 ────────────────────────────────────────────────

class TestRewardAggregatorPhase6:
    def test_r6_r7_included_in_total(self):
        agg = RewardAggregator()
        components = RewardComponents(
            r1_hook_strength=0.8,
            r2_coherence=0.7,
            r3_cultural_alignment=0.75,
            r4_debate_resolution=0.6,
            r5_defender_preservation=0.7,
            r6_safety=1.0,
            r7_originality=0.9,
        )
        start = RewardComponents(
            r1_hook_strength=0.5,
            r2_coherence=0.5,
            r3_cultural_alignment=0.5,
            r4_debate_resolution=0.5,
            r5_defender_preservation=0.5,
            r6_safety=1.0,
            r7_originality=0.9,
        )
        result, log = agg.compute(components, start, [], episode_id="test", step_num=1)
        assert result.total > 0.0
        assert not log.triggered

    def test_catastrophic_drop_fires_on_r6_zero(self):
        agg = RewardAggregator()
        components = RewardComponents(
            r1_hook_strength=0.8,
            r2_coherence=0.7,
            r3_cultural_alignment=0.75,
            r4_debate_resolution=0.6,
            r5_defender_preservation=0.7,
            r6_safety=0.0,
            r7_originality=0.9,
        )
        start = RewardComponents(
            r1_hook_strength=0.8,
            r2_coherence=0.7,
            r3_cultural_alignment=0.75,
            r4_debate_resolution=0.6,
            r5_defender_preservation=0.7,
            r6_safety=1.0,
            r7_originality=0.9,
        )
        result, log = agg.compute(components, start, [], episode_id="test", step_num=1)
        assert result.total == 0.0
        assert log.triggered
        assert log.rule_triggered == "r6_safety_hard_zero"


# ── env.step() integration ─────────────────────────────────────────────────────

class TestEnvStepPhase6:
    def test_step_includes_moderation_and_originality(self, monkeypatch):
        from unittest.mock import MagicMock
        from viral_script_engine.environment.env import ViralScriptEnv
        from viral_script_engine.agents.critic import CritiqueOutput, CritiqueClaim
        from viral_script_engine.agents.defender import DefenderOutput
        from viral_script_engine.agents.rewriter import RewriteResult

        env = ViralScriptEnv(
            scripts_path=str(BASE_DIR / "data" / "test_scripts" / "scripts.json"),
            max_steps=1,
            difficulty="easy",
            use_escalation=False,
        )

        dummy_claim = CritiqueClaim(
            claim_id="C1",
            critique_class="hook_weakness",
            claim_text="Hook is weak",
            timestamp_range="0-3s",
            evidence="Opening is vague",
            is_falsifiable=True,
            severity="medium",
        )
        dummy_critique = CritiqueOutput(
            claims=[dummy_claim],
            overall_severity="medium",
            raw_response="Hook is weak",
        )
        dummy_defender = DefenderOutput(
            core_strength="The hook has genuine curiosity value.",
            core_strength_quote="First sentence",
            defense_argument="The structure is sound; only specificity needs improvement.",
            flagged_critic_claims=["C1"],
            regional_voice_elements=["regional phrase"],
        )
        dummy_rewrite = RewriteResult(
            rewritten_script="3 things nobody tells you about morning routines that actually work.",
            diff="- Old hook\n+ 3 things nobody tells you about morning routines that actually work.",
            word_count_delta=2,
        )

        from viral_script_engine.rewards.r4_debate_resolution import DebateResolutionResult
        dummy_r4 = DebateResolutionResult(
            score=0.7,
            resolution_status="resolved",
            original_claim_id="C1",
            original_claim_class="hook_weakness",
            new_claims_count=0,
        )

        monkeypatch.setattr(env.critic, "critique", lambda *a, **kw: dummy_critique)
        monkeypatch.setattr(env.defender, "defend", lambda **kw: dummy_defender)
        monkeypatch.setattr(env.rewriter, "rewrite", lambda script, action: dummy_rewrite)
        monkeypatch.setattr(env.r4, "score", lambda **kw: dummy_r4)

        env.reset()
        action = {
            "action_type": "hook_rewrite",
            "target_section": "hook",
            "instruction": "Make the hook more engaging.",
            "critique_claim_id": "C1",
            "reasoning": "test",
        }
        _, _, _, _, info = env.step(action)
        assert "moderation_output" in info
        assert "originality_output" in info
        rc = info["reward_components"]
        assert rc.get("r6_safety") is not None
        assert rc.get("r7_originality") is not None
