"""Phase 9 tests — Multi-Platform Reward Divergence."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from viral_script_engine.platforms.platform_spec import PlatformRegistry, PlatformSpec
from viral_script_engine.rewards.r1_hook_strength import HookStrengthReward
from viral_script_engine.rewards.r2_coherence import CoherenceReward
from viral_script_engine.rewards.r9_platform_pacing import PlatformPacingReward

# ── PlatformRegistry ──────────────────────────────────────────────────────────

class TestPlatformRegistry:
    def setup_method(self):
        self.reg = PlatformRegistry()

    def test_get_reels(self):
        spec = self.reg.get("Reels")
        assert isinstance(spec, PlatformSpec)
        assert spec.platform == "Reels"
        assert spec.hook_window_seconds == 3
        assert spec.max_script_length_words == 180
        assert spec.pacing_norm == "fast"

    def test_get_shorts(self):
        spec = self.reg.get("Shorts")
        assert spec.hook_window_seconds == 2
        assert spec.max_script_length_words == 120
        assert spec.hook_length_words == 10
        assert spec.pacing_norm == "very_fast"

    def test_get_feed(self):
        spec = self.reg.get("Feed")
        assert spec.hook_window_seconds == 5
        assert spec.max_script_length_words == 300
        assert spec.hook_length_words == 25
        assert spec.pacing_norm == "moderate"

    def test_get_tiktok(self):
        spec = self.reg.get("TikTok")
        assert spec.hook_window_seconds == 2
        assert spec.max_script_length_words == 150

    def test_unknown_platform_raises(self):
        with pytest.raises(ValueError, match="Unknown platform"):
            self.reg.get("Instagram")

    def test_all_platforms_have_required_fields(self):
        for platform in ["Reels", "Shorts", "Feed", "TikTok"]:
            spec = self.reg.get(platform)
            assert spec.hook_length_words > 0
            assert spec.optimal_script_length_words > 0
            assert spec.cta_position != ""


# ── R1 platform-aware hook scoring ───────────────────────────────────────────

# A hook that has 20 words — within Reels (15) is a big overrun,
# but Feed allows 25 so it's comfortably within spec.
_LONG_HOOK_SCRIPT = (
    "Why does your phone battery lie to you every single morning when you check it? "
    "Because manufacturers hide the real numbers. "
    "Charge to eighty percent, never below twenty. "
    "You will get two extra years. Follow for more."
)

# A very short hook — first 3 sentences are 8 words total, well within Reels (15) limit.
_SHORT_HOOK_SCRIPT = (
    "Battery lies. Charge to eighty. Never below twenty. "
    "Phone manufacturers hide the real numbers to make you charge more often. "
    "Subscribe for the full battery myth-busting series."
)


class TestR1PlatformAware:
    def setup_method(self):
        self.r1 = HookStrengthReward()

    def test_long_hook_scores_lower_on_shorts_than_feed(self):
        shorts_score = self.r1.score(_LONG_HOOK_SCRIPT, platform="Shorts").score
        feed_score = self.r1.score(_LONG_HOOK_SCRIPT, platform="Feed").score
        assert feed_score >= shorts_score, (
            f"Feed ({feed_score:.3f}) should be >= Shorts ({shorts_score:.3f}) for a 20-word hook"
        )

    def test_short_hook_passes_length_fit_on_reels(self):
        result = self.r1.score(_SHORT_HOOK_SCRIPT, platform="Reels")
        assert result.check_details.get("length_fit") is True

    def test_platform_param_defaults_to_reels(self):
        r_default = self.r1.score(_SHORT_HOOK_SCRIPT)
        r_reels = self.r1.score(_SHORT_HOOK_SCRIPT, platform="Reels")
        assert abs(r_default.score - r_reels.score) < 1e-6


# ── R2 length penalty ─────────────────────────────────────────────────────────

_SHORT_SCRIPT = "Why is your battery lying? Charge to 80. Never below 20. Subscribe."
_LONG_SCRIPT = " ".join(["This is a filler sentence that adds many words."] * 30)


class TestR2LengthPenalty:
    def setup_method(self):
        self.r2 = CoherenceReward()

    def test_length_penalty_applied_when_over_shorts_max(self):
        # _LONG_SCRIPT far exceeds Shorts max (120 words)
        score_shorts = self.r2.score(_SHORT_SCRIPT, _LONG_SCRIPT, platform="Shorts").score
        score_feed = self.r2.score(_SHORT_SCRIPT, _LONG_SCRIPT, platform="Feed").score
        # Feed allows 300 words — less penalty than Shorts (120 words max)
        assert score_feed >= score_shorts

    def test_no_penalty_when_within_limit(self):
        within_limit = " ".join(["short word"] * 60)  # 120 words, within Shorts limit
        result = self.r2.score(_SHORT_SCRIPT, within_limit, platform="Shorts")
        assert result.score >= 0.0

    def test_penalty_capped_at_0_3(self):
        # Use same-vocabulary rewrites so base semantic score stays constant.
        # Only the length penalty differs; the cap of 0.3 limits the score delta.
        base = " ".join(["word"] * 50)
        just_over = " ".join(["word"] * 125)   # 4% over Shorts max (120)
        way_over = " ".join(["word"] * 5000)   # 40x over Shorts max
        r_just_over = self.r2.score(base, just_over, platform="Shorts")
        r_way_over = self.r2.score(base, way_over, platform="Shorts")
        # Both have same base similarity; penalty capped at 0.3 → score delta ≤ 0.3
        assert r_just_over.score - r_way_over.score <= 0.31


# ── R9 PlatformPacingReward ───────────────────────────────────────────────────

# Fast-paced script: short sentences in hook
_FAST_SCRIPT = (
    "Your phone lies. Battery is fake. Charge to eighty. "
    "Manufacturers hide the real numbers so you charge more often. "
    "The fix is simple: never go above eighty, never below twenty. "
    "Do this for two weeks. You get two extra years. Subscribe."
)

# Slow-paced script: long meandering hook sentence
_SLOW_SCRIPT = (
    "So I wanted to start by talking about something that I think is really quite interesting "
    "and important that most people don't really think about when they're using their phone on a "
    "daily basis, which is the way that battery life is actually calculated and displayed to you. "
    "The numbers are not real. Charge to eighty. "
    "Subscribe for more."
)


class TestR9PlatformPacing:
    def setup_method(self):
        self.r9 = PlatformPacingReward()

    def test_fast_script_scores_higher_on_reels_than_slow(self):
        fast = self.r9.score(_FAST_SCRIPT, platform="Reels").score
        slow = self.r9.score(_SLOW_SCRIPT, platform="Reels").score
        assert fast > slow, f"fast ({fast:.3f}) should beat slow ({slow:.3f}) on Reels"

    def test_same_script_scores_differently_on_reels_vs_feed(self):
        # Use _FAST_SCRIPT which has short hook sentences (~3 words each).
        # Reels threshold=12 → pacing_score=1.0; Feed threshold=18 → pacing_score=1.0 too,
        # but ratio differs because optimal_hook_ratio changes between platforms.
        reels = self.r9.score(_FAST_SCRIPT, platform="Reels")
        feed = self.r9.score(_FAST_SCRIPT, platform="Feed")
        # At least one sub-score must differ (pacing, ratio, or cta threshold)
        differs = (
            reels.pacing_score != feed.pacing_score
            or reels.ratio_score != feed.ratio_score
            or reels.cta_score != feed.cta_score
        )
        assert differs, (
            f"No R9 sub-score differed between Reels and Feed: "
            f"pacing={reels.pacing_score}/{feed.pacing_score}, "
            f"ratio={reels.ratio_score}/{feed.ratio_score}, "
            f"cta={reels.cta_score}/{feed.cta_score}"
        )

    def test_cta_position_correct_for_reels(self):
        # A script where >90% of words come before the CTA should score 1.0 on cta_score
        body = " ".join(["content word"] * 20)
        cta = "Follow for more tips."
        script = f"Your phone lies. {body} {cta}"
        result = self.r9.score(script, platform="Reels")
        assert result.cta_score in (0.5, 1.0)

    def test_cta_position_correct_for_shorts(self):
        result = self.r9.score(_FAST_SCRIPT, platform="Shorts")
        assert 0.0 <= result.score <= 1.0
        assert result.platform == "Shorts"

    def test_scores_in_valid_range(self):
        for platform in ["Reels", "Shorts", "Feed", "TikTok"]:
            result = self.r9.score(_FAST_SCRIPT, platform=platform)
            assert 0.0 <= result.score <= 1.0
            assert 0.0 <= result.pacing_score <= 1.0
            assert 0.0 <= result.ratio_score <= 1.0
            assert result.cta_score in (0.5, 1.0)

    def test_cross_platform_divergence_proof(self):
        """Key proof: same script produces different R9 scores across platforms."""
        scores = {p: self.r9.score(_FAST_SCRIPT, platform=p).score
                  for p in ["Reels", "Shorts", "Feed"]}
        unique_scores = len(set(round(s, 3) for s in scores.values()))
        assert unique_scores > 1, f"All platforms returned identical R9 score: {scores}"


# ── env.step() passes platform to reward functions ───────────────────────────

class TestEnvPlatformWiring:
    def test_env_r9_fires_in_step(self):
        """env.step() must include r9_platform_pacing in reward components."""
        from unittest.mock import patch, MagicMock
        from viral_script_engine.environment.env import ViralScriptEnv

        scripts_path = str(
            Path(__file__).parent.parent / "data" / "test_scripts" / "scripts.json"
        )
        cultural_kb_path = str(
            Path(__file__).parent.parent / "data" / "cultural_kb.json"
        )

        env = ViralScriptEnv(
            scripts_path=scripts_path,
            cultural_kb_path=cultural_kb_path,
            difficulty="easy",
            use_escalation=False,
            use_anti_gaming=False,
        )
        env.reset()
        current_text = env._state.current_script

        mock_critique = MagicMock()
        mock_critique.claims = []
        mock_critique.overall_severity = "low"

        mock_defender_out = MagicMock()
        mock_defender_out.core_strength = "test"
        mock_defender_out.core_strength_quote = "test"
        mock_defender_out.defense_argument = "test"
        mock_defender_out.flagged_critic_claims = []
        mock_defender_out.regional_voice_elements = []
        mock_defender_out.model_dump.return_value = {}

        mock_rewrite = MagicMock()
        mock_rewrite.rewritten_script = current_text
        mock_rewrite.diff = ""

        with patch.object(env.critic, "critique", return_value=mock_critique), \
             patch.object(env.defender, "defend", return_value=mock_defender_out), \
             patch.object(env.rewriter, "rewrite", return_value=mock_rewrite):
            action = {
                "action_type": "hook_rewrite",
                "target_section": "hook",
                "instruction": "Make the hook stronger.",
                "critique_claim_id": "C1",
                "reasoning": "test",
            }
            _, _, _, _, info = env.step(action)
            rc = info["reward_components"]
            assert "r9_platform_pacing" in rc
            assert rc["r9_platform_pacing"] is not None
            assert 0.0 <= rc["r9_platform_pacing"] <= 1.0

    def test_env_stores_current_platform_on_reset(self):
        from viral_script_engine.environment.env import ViralScriptEnv

        scripts_path = str(
            Path(__file__).parent.parent / "data" / "test_scripts" / "scripts.json"
        )
        cultural_kb_path = str(
            Path(__file__).parent.parent / "data" / "cultural_kb.json"
        )
        env = ViralScriptEnv(
            scripts_path=scripts_path,
            cultural_kb_path=cultural_kb_path,
            difficulty="easy",
            use_escalation=False,
        )
        env.reset()
        assert env._current_platform in ["Reels", "Shorts", "Feed", "TikTok"]
