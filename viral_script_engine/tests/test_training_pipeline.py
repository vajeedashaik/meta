"""
Tests for Phase 3 — Training Pipeline.

Run: pytest viral_script_engine/tests/test_training_pipeline.py -v
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

BASE_DIR = Path(__file__).parent.parent
CURRICULUM_DIR = BASE_DIR / "data" / "curriculum"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dummy_episode_config():
    return {
        "episode_config_id": "easy_001",
        "difficulty": "easy",
        "script_id": "S01",
        "script_text": (
            "Okay so real talk — I've been broke my whole life. "
            "One trick changed everything. Mutual funds. Just SIPs."
        ),
        "region": "Mumbai Gen Z",
        "platform": "Reels",
        "niche": "personal finance",
        "dominant_flaw": "buried_hook",
        "expected_critique_class": "hook_weakness",
        "expected_action": "hook_rewrite",
        "curriculum_notes": "One obvious flaw.",
    }


@pytest.fixture
def mock_env(dummy_episode_config):
    env = MagicMock()
    env.max_steps = 5
    obs = {
        "current_script": dummy_episode_config["script_text"],
        "original_script": dummy_episode_config["script_text"],
        "region": dummy_episode_config["region"],
        "platform": dummy_episode_config["platform"],
        "niche": dummy_episode_config["niche"],
        "step_num": 0,
        "max_steps": 5,
        "debate_history": [],
        "reward_components": {
            "r1_hook_strength": 0.4,
            "r2_coherence": 0.6,
            "r3_cultural_alignment": 0.5,
            "r4_debate_resolution": None,
            "r5_defender_preservation": None,
            "total": 0.5,
        },
        "difficulty_level": "easy",
        "episode_id": "test-episode-001",
    }
    env.reset.return_value = (obs, {})
    env.reset_from_config.return_value = (obs, {})
    env.step.return_value = (
        obs,
        0.65,
        True,
        False,
        {
            "reward_components": obs["reward_components"],
            "anti_gaming_triggered": False,
            "anti_gaming_log": {"triggered": False, "penalty_applied": 0.0},
        },
    )
    return env


@pytest.fixture
def mock_model():
    def _model(prompt: str) -> str:
        return json.dumps({
            "action_type": "hook_rewrite",
            "target_section": "hook",
            "instruction": "Open with the most surprising claim immediately.",
            "critique_claim_id": "C1",
            "reasoning": "The hook is buried — move the key reveal to line 1.",
        })
    return _model


# ---------------------------------------------------------------------------
# Test 1: build_training_prompts returns non-empty dataset with correct format
# ---------------------------------------------------------------------------

def test_build_training_prompts_easy():
    """build_training_prompts('easy') returns non-empty list with correct prompt format."""
    if not (CURRICULUM_DIR / "easy_tier.jsonl").exists():
        pytest.skip("easy_tier.jsonl not found — run build_curriculum.py first")

    from viral_script_engine.training.rollout_function import build_training_prompts
    prompts = build_training_prompts("easy")

    assert len(prompts) > 0, "Should return at least one prompt"
    first = prompts[0]
    assert "##EPISODE_CONFIG##" in first, "Prompt must contain embedded episode config header"
    assert "##END_CONFIG##" in first, "Prompt must contain end-config marker"
    assert "<|system|>" in first, "Prompt must include system role tag"
    assert "CURRENT SCRIPT:" in first, "Prompt must include script section"
    assert "AVAILABLE ACTIONS:" in first, "Prompt must list available actions"


def test_build_training_prompts_config_parseable():
    """Episode config embedded in prompt must be valid JSON."""
    if not (CURRICULUM_DIR / "easy_tier.jsonl").exists():
        pytest.skip("easy_tier.jsonl not found")

    import re
    from viral_script_engine.training.rollout_function import build_training_prompts
    prompts = build_training_prompts("easy")

    for prompt in prompts[:3]:
        match = re.search(r"##EPISODE_CONFIG##\s*(\{.*?\})\s*##END_CONFIG##", prompt, re.DOTALL)
        assert match, "Config header must be parseable"
        config = json.loads(match.group(1))
        assert "script_text" in config
        assert "region" in config
        assert "difficulty" in config


# ---------------------------------------------------------------------------
# Test 2: rollout_fn completes one episode given a mock model returning valid JSON
# ---------------------------------------------------------------------------

def test_rollout_fn_single_episode(mock_env, mock_model, dummy_episode_config):
    """rollout_fn completes one episode and returns (completions, rewards)."""
    from viral_script_engine.training.rollout_function import build_rollout_fn, _config_to_prompt

    rollout_fn = build_rollout_fn(mock_env, max_steps=5)
    prompt = _config_to_prompt(dummy_episode_config)

    completions, rewards = rollout_fn([prompt], model=mock_model, tokenizer=None)

    assert len(completions) == 1
    assert len(rewards) == 1
    assert isinstance(rewards[0], float)
    assert 0.0 <= rewards[0] <= 1.0, "Reward should be in [0, 1]"


def test_rollout_fn_batch(mock_env, mock_model, dummy_episode_config):
    """rollout_fn handles a batch of prompts."""
    from viral_script_engine.training.rollout_function import build_rollout_fn, _config_to_prompt

    rollout_fn = build_rollout_fn(mock_env, max_steps=5)
    prompt = _config_to_prompt(dummy_episode_config)

    completions, rewards = rollout_fn([prompt] * 3, model=mock_model, tokenizer=None)

    assert len(completions) == 3
    assert len(rewards) == 3


# ---------------------------------------------------------------------------
# Test 3: GRPOConfig builds without error
# ---------------------------------------------------------------------------

def test_grpo_config_builds():
    """GRPOConfig builds without error when trl is installed and pyarrow DLL is available."""
    try:
        from trl import GRPOConfig
    except Exception:
        pytest.skip("trl/GRPOConfig not available on this machine (pyarrow DLL or import issue)")

    from viral_script_engine.training.train_grpo import build_grpo_config
    with tempfile.TemporaryDirectory() as tmpdir:
        config = build_grpo_config(output_dir=tmpdir, num_steps=200, dry_run=True)
        assert config.max_steps == 5
        assert config.per_device_train_batch_size == 1


# ---------------------------------------------------------------------------
# Test 4: Model saving uses save_pretrained_merged
# ---------------------------------------------------------------------------

def test_model_save_uses_merged():
    """Training script uses save_pretrained_merged, not save_pretrained."""
    train_script = Path(__file__).parent.parent / "training" / "train_grpo.py"
    content = train_script.read_text(encoding="utf-8")

    assert "save_pretrained_merged" in content, (
        "train_grpo.py must use model.save_pretrained_merged() — "
        "naive upcast from 4-bit is not supported"
    )
    # Ensure the naive form is only in comments or strings, not as a bare call
    import re
    bare_calls = re.findall(r"model\.save_pretrained\(", content)
    assert len(bare_calls) == 0, (
        "train_grpo.py must NOT use model.save_pretrained() — use save_pretrained_merged"
    )


# ---------------------------------------------------------------------------
# Test 5: plot_training_curves generates PNG given valid JSON inputs
# ---------------------------------------------------------------------------

def test_plot_training_curves_generates_png():
    """plot_training_curves() generates a PNG file given valid JSON inputs."""
    from viral_script_engine.training.reward_curves import plot_training_curves

    episode_template = {
        "episode_num": 1,
        "difficulty": "easy",
        "total_reward": 0.55,
        "steps": [
            {"r1": 0.6, "r2": 0.5, "r3": 0.4, "r4": 0.5, "r5": 0.6, "total": 0.55}
        ],
    }

    baseline = [dict(episode_template, episode_num=i, total_reward=0.4 + i * 0.01)
                for i in range(1, 21)]
    trained = [dict(episode_template, episode_num=i, total_reward=0.55 + i * 0.01)
               for i in range(1, 21)]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        base_path = tmpdir / "baseline_results.json"
        train_path = tmpdir / "training_results.json"
        out_path = tmpdir / "training_vs_baseline.png"

        base_path.write_text(json.dumps(baseline))
        train_path.write_text(json.dumps(trained))

        plot_training_curves(
            baseline_log_path=str(base_path),
            training_log_path=str(train_path),
            output_path=str(out_path),
        )

        assert out_path.exists(), "PNG file must be created"
        assert out_path.stat().st_size > 1000, "PNG file must be non-trivial"
        pdf_path = out_path.with_suffix(".pdf")
        assert pdf_path.exists(), "PDF file must also be created"


# ---------------------------------------------------------------------------
# Test 6: Env reset_from_config works correctly
# ---------------------------------------------------------------------------

def test_env_reset_from_config(dummy_episode_config):
    """ViralScriptEnv.reset_from_config() resets state from a given config."""
    from viral_script_engine.environment.env import ViralScriptEnv
    from viral_script_engine.rewards import r2_coherence, r5_defender_preservation

    class _FakeR2:
        score = 0.75
        raw_similarity = 0.85
        interpretation = "good_coherence"

    class _FakeR5:
        score = 0.70
        max_similarity = 0.80
        best_matching_sentence = "[test mock]"

    r2_coherence.CoherenceReward.score = lambda self, a, b: _FakeR2()
    r5_defender_preservation.DefenderPreservationReward.score = lambda self, d, s: _FakeR5()

    env = ViralScriptEnv(
        scripts_path=str(BASE_DIR / "data" / "test_scripts" / "scripts.json"),
        cultural_kb_path=str(BASE_DIR / "data" / "cultural_kb.json"),
        max_steps=5,
        difficulty="easy",
    )

    obs, info = env.reset_from_config(dummy_episode_config)

    assert obs["current_script"] == dummy_episode_config["script_text"]
    assert obs["region"] == dummy_episode_config["region"]
    assert obs["platform"] == dummy_episode_config["platform"]
    assert obs["niche"] == dummy_episode_config["niche"]
    assert obs["step_num"] == 0
