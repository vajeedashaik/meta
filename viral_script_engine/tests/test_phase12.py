"""Phase 12 tests — Retention Curve Simulator."""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from viral_script_engine.retention.feature_extractor import (
    FeatureExtractor,
    ScriptFeatures,
    _KNOWN_PLATFORMS,
)
from viral_script_engine.retention.curve_predictor import (
    RetentionCurve,
    RetentionCurvePredictor,
    CURVE_TIMEPOINTS,
)
from viral_script_engine.retention.curve_scorer import RetentionCurveScorer
from viral_script_engine.rewards.r10_retention_curve import RetentionCurveReward

_SCRIPTS_PATH = str(
    Path(__file__).parent.parent / "data" / "test_scripts" / "scripts.json"
)
_CULTURAL_KB_PATH = str(
    Path(__file__).parent.parent / "data" / "cultural_kb.json"
)

_GOOD_SCRIPT = (
    "Did you know 80% of people get this wrong? Here's what actually works. "
    "Stop doing what everyone tells you. Use this one simple method instead. "
    "The results will surprise you. Follow for more."
)
_BAD_SCRIPT = (
    "Hello guys welcome back um so today basically I wanted to kind of talk "
    "about you know like finances and stuff. So basically just try to save money."
)


# ---------------------------------------------------------------------------
# FeatureExtractor tests
# ---------------------------------------------------------------------------

def test_feature_extractor_produces_correct_features():
    extractor = FeatureExtractor(cultural_kb_path=_CULTURAL_KB_PATH)
    features = extractor.extract(_GOOD_SCRIPT, platform="Reels", region="pan_india_english")

    assert isinstance(features, ScriptFeatures)
    assert features.hook_word_count > 0
    assert features.sentence_count > 0
    assert features.word_count > 0
    assert features.platform == "Reels"
    assert features.hook_has_number is True  # "80%"
    assert features.hook_has_question is True  # "?"


def test_feature_extractor_bad_script_has_high_filler():
    extractor = FeatureExtractor(cultural_kb_path=_CULTURAL_KB_PATH)
    features = extractor.extract(_BAD_SCRIPT, platform="Reels", region="pan_india_english")

    # Bad script should have higher filler score than good script
    good_features = extractor.extract(_GOOD_SCRIPT, platform="Reels", region="pan_india_english")
    assert features.hook_filler_score >= good_features.hook_filler_score


def test_to_vector_returns_flat_numeric_list():
    extractor = FeatureExtractor(cultural_kb_path=_CULTURAL_KB_PATH)
    features = extractor.extract(_GOOD_SCRIPT, platform="Reels", region="pan_india_english")
    vec = features.to_vector()

    assert isinstance(vec, list)
    assert len(vec) > 0
    # No NaN values
    for v in vec:
        assert v == v, f"NaN found in vector: {vec}"
    # All values are floats
    for v in vec:
        assert isinstance(v, (int, float))


def test_to_vector_platform_one_hot():
    extractor = FeatureExtractor(cultural_kb_path=_CULTURAL_KB_PATH)
    for platform in _KNOWN_PLATFORMS:
        features = extractor.extract(_GOOD_SCRIPT, platform=platform, region="pan_india_english")
        vec = features.to_vector()
        # Last N elements are one-hot platform encoding
        platform_slice = vec[-len(_KNOWN_PLATFORMS):]
        assert sum(platform_slice) == 1.0, f"One-hot sum should be 1 for {platform}"
        assert max(platform_slice) == 1.0


def test_to_vector_no_nan_for_bad_script():
    extractor = FeatureExtractor(cultural_kb_path=_CULTURAL_KB_PATH)
    features = extractor.extract(_BAD_SCRIPT, platform="TikTok", region="pan_india_english")
    vec = features.to_vector()
    for v in vec:
        assert v == v, f"NaN found in vector"


# ---------------------------------------------------------------------------
# RetentionCurvePredictor tests
# ---------------------------------------------------------------------------

def test_predictor_raises_if_not_trained():
    predictor = RetentionCurvePredictor.__new__(RetentionCurvePredictor)
    predictor.model = None
    predictor._trained = False
    extractor = FeatureExtractor(cultural_kb_path=_CULTURAL_KB_PATH)
    features = extractor.extract(_GOOD_SCRIPT, platform="Reels", region="pan_india_english")

    with pytest.raises(RuntimeError, match="not trained"):
        predictor.predict(features)


def _make_trained_predictor() -> RetentionCurvePredictor:
    """Train predictor on a minimal in-memory dataset."""
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.multioutput import MultiOutputRegressor
    import numpy as np

    extractor = FeatureExtractor(cultural_kb_path=_CULTURAL_KB_PATH)
    scripts = [_GOOD_SCRIPT, _BAD_SCRIPT] * 10
    platforms = ["Reels", "TikTok", "Shorts", "Feed"] * 5
    X, y = [], []
    for i, (sc, pl) in enumerate(zip(scripts, platforms)):
        feat = extractor.extract(sc, platform=pl, region="pan_india_english")
        X.append(feat.to_vector())
        quality = 1.0 if sc == _GOOD_SCRIPT else 0.3
        curve = [max(0.0, quality - j * 0.05) for j in range(len(CURVE_TIMEPOINTS))]
        y.append(curve)

    model = MultiOutputRegressor(
        GradientBoostingRegressor(n_estimators=10, max_depth=2, random_state=42)
    )
    model.fit(np.array(X), np.array(y))

    predictor = RetentionCurvePredictor.__new__(RetentionCurvePredictor)
    predictor.model = model
    predictor._trained = True
    return predictor


def test_predicted_curve_is_monotonically_non_increasing():
    predictor = _make_trained_predictor()
    extractor = FeatureExtractor(cultural_kb_path=_CULTURAL_KB_PATH)
    features = extractor.extract(_GOOD_SCRIPT, platform="Reels", region="pan_india_english")
    curve = predictor.predict(features)

    for i in range(1, len(curve.values)):
        assert curve.values[i] <= curve.values[i - 1] + 1e-9, (
            f"Curve not monotonic at index {i}: {curve.values[i - 1]} -> {curve.values[i]}"
        )


def test_predicted_curve_values_in_range():
    predictor = _make_trained_predictor()
    extractor = FeatureExtractor(cultural_kb_path=_CULTURAL_KB_PATH)
    features = extractor.extract(_BAD_SCRIPT, platform="TikTok", region="pan_india_english")
    curve = predictor.predict(features)

    for v in curve.values:
        assert 0.0 <= v <= 1.0, f"Value {v} out of [0, 1]"


def test_predicted_curve_has_correct_timepoints():
    predictor = _make_trained_predictor()
    extractor = FeatureExtractor(cultural_kb_path=_CULTURAL_KB_PATH)
    features = extractor.extract(_GOOD_SCRIPT, platform="Reels", region="pan_india_english")
    curve = predictor.predict(features)

    assert curve.timepoints == CURVE_TIMEPOINTS
    assert len(curve.values) == len(CURVE_TIMEPOINTS)


# ---------------------------------------------------------------------------
# RetentionCurveScorer tests
# ---------------------------------------------------------------------------

def _make_curve(values: list) -> RetentionCurve:
    return RetentionCurve.from_values(values)


def test_scorer_rewards_targeted_improvement():
    scorer = RetentionCurveScorer()
    # hook_rewrite targets [0, 3, 6] — improve those timepoints
    orig_values = [1.0, 0.6, 0.5, 0.45, 0.42, 0.40, 0.38, 0.36, 0.32, 0.30]
    new_values  = [1.0, 0.85, 0.75, 0.45, 0.42, 0.40, 0.38, 0.36, 0.32, 0.30]

    result = scorer.score(
        original_curve=_make_curve(orig_values),
        new_curve=_make_curve(new_values),
        action_type="hook_rewrite",
    )
    assert result.final_score > 0
    assert result.targeted_improvement > 0
    assert 3 in result.improved_timepoints or 6 in result.improved_timepoints


def test_scorer_applies_regression_penalty_for_worsening():
    scorer = RetentionCurveScorer()
    orig_values = [1.0, 0.9, 0.8, 0.7, 0.65, 0.60, 0.55, 0.50, 0.45, 0.40]
    # Worsen the mid-video section
    new_values  = [1.0, 0.9, 0.8, 0.5, 0.45, 0.40, 0.55, 0.50, 0.45, 0.40]

    result = scorer.score(
        original_curve=_make_curve(orig_values),
        new_curve=_make_curve(new_values),
        action_type="hook_rewrite",
    )
    assert result.regression_penalty > 0
    assert len(result.worsened_timepoints) > 0


def test_scorer_score_in_range():
    scorer = RetentionCurveScorer()
    orig_values = [1.0, 0.8, 0.7, 0.6, 0.55, 0.50, 0.46, 0.42, 0.38, 0.35]
    new_values  = [1.0, 0.85, 0.75, 0.65, 0.60, 0.55, 0.50, 0.46, 0.42, 0.38]

    result = scorer.score(
        original_curve=_make_curve(orig_values),
        new_curve=_make_curve(new_values),
        action_type="section_reorder",
    )
    assert 0.0 <= result.final_score <= 1.0


# ---------------------------------------------------------------------------
# RetentionCurveReward — cache test
# ---------------------------------------------------------------------------

def test_retention_reward_caches_original_curve():
    """FeatureExtractor.extract should be called only once for the original script per episode."""
    predictor = _make_trained_predictor()
    reward = RetentionCurveReward.__new__(RetentionCurveReward)
    reward.extractor = FeatureExtractor(cultural_kb_path=_CULTURAL_KB_PATH)
    reward.predictor = predictor
    reward.scorer = RetentionCurveScorer()
    reward._original_curve_cache = {}

    call_count = {"n": 0}
    original_extract = reward.extractor.extract

    def counting_extract(script, platform, region):
        call_count["n"] += 1
        return original_extract(script, platform, region)

    reward.extractor.extract = counting_extract

    episode_id = "ep_cache_test"
    for _ in range(3):
        reward.score(
            original_script=_GOOD_SCRIPT,
            rewritten_script=_BAD_SCRIPT,
            platform="Reels",
            region="pan_india_english",
            action_type="hook_rewrite",
            episode_id=episode_id,
        )

    # extract called for original once + rewritten on every call = 1 + 3 = 4
    # original is cached after first call → only 1 for original, 3 for rewritten = 4 total
    assert call_count["n"] == 4, (
        f"Expected 4 extract calls (1 original cached + 3 rewritten), got {call_count['n']}"
    )


# ---------------------------------------------------------------------------
# env.step includes r10 in reward components
# ---------------------------------------------------------------------------

def test_env_step_includes_r10_when_model_trained():
    """env.step() should include r10_retention_curve in reward components when model is trained."""
    from viral_script_engine.environment.env import ViralScriptEnv
    from unittest.mock import MagicMock

    env = ViralScriptEnv(
        scripts_path=_SCRIPTS_PATH,
        cultural_kb_path=_CULTURAL_KB_PATH,
        difficulty="easy",
        use_escalation=False,
        use_anti_gaming=False,
    )

    # Inject trained predictor
    predictor = _make_trained_predictor()
    env.r10.predictor = predictor

    obs, _ = env.reset()

    mock_critique = MagicMock()
    mock_critique.claims = []
    mock_critique.overall_severity = "low"

    mock_defender = MagicMock()
    mock_defender.core_strength = "Strong hook"
    mock_defender.core_strength_quote = "Test quote"
    mock_defender.defense_argument = "Good"
    mock_defender.flagged_critic_claims = []
    mock_defender.regional_voice_elements = []
    mock_defender.model_dump.return_value = {}

    mock_rewrite = MagicMock()
    mock_rewrite.rewritten_script = obs["current_script"]
    mock_rewrite.diff = ""

    with patch.object(env.critic, "critique", return_value=mock_critique), \
         patch.object(env.defender, "defend", return_value=mock_defender), \
         patch.object(env.rewriter, "rewrite", return_value=mock_rewrite):

        _, _, _, _, info = env.step({
            "action_type": "hook_rewrite",
            "target_section": "hook",
            "instruction": "Strengthen the hook.",
            "critique_claim_id": "C1",
            "reasoning": "test",
        })

    rc = info["reward_components"]
    assert "r10_retention_curve" in rc
    assert rc["r10_retention_curve"] is not None
    assert 0.0 <= rc["r10_retention_curve"] <= 1.0
