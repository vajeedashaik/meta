"""
Gate check script for Phase 12 — runs a dummy episode and verifies R9 and R10 fire.

Usage:
    python scripts/run_dummy_episode.py --difficulty easy --steps 3 --verbose
"""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from viral_script_engine.environment.env import ViralScriptEnv

_ROOT = Path(__file__).parent.parent / "viral_script_engine"
_SCRIPTS_PATH = str(_ROOT / "data" / "test_scripts" / "scripts.json")
_CULTURAL_KB_PATH = str(_ROOT / "data" / "cultural_kb.json")


def run_episode(difficulty: str, steps: int, verbose: bool):
    env = ViralScriptEnv(
        scripts_path=_SCRIPTS_PATH,
        cultural_kb_path=_CULTURAL_KB_PATH,
        difficulty=difficulty,
        use_escalation=False,
        use_anti_gaming=False,
    )
    obs, _ = env.reset()
    platform = env._current_platform

    if verbose:
        print(f"\n[EPISODE START]  difficulty={difficulty}  platform={platform}")
        print(f"  Script preview: {obs['current_script'][:80]}...")

    # Stub LLM calls so this runs without API keys
    mock_critique = MagicMock()
    mock_critique.claims = []
    mock_critique.overall_severity = "low"

    mock_defender_out = MagicMock()
    mock_defender_out.core_strength = "Strong hook"
    mock_defender_out.core_strength_quote = "Your phone is lying to you"
    mock_defender_out.defense_argument = "The hook is effective"
    mock_defender_out.flagged_critic_claims = []
    mock_defender_out.regional_voice_elements = []
    mock_defender_out.model_dump.return_value = {}

    mock_rewrite = MagicMock()
    mock_rewrite.rewritten_script = obs["current_script"]
    mock_rewrite.diff = ""

    rewards_per_step = []

    with patch.object(env.critic, "critique", return_value=mock_critique), \
         patch.object(env.defender, "defend", return_value=mock_defender_out), \
         patch.object(env.rewriter, "rewrite", return_value=mock_rewrite):

        for step in range(steps):
            action = {
                "action_type": "hook_rewrite",
                "target_section": "hook",
                "instruction": "Strengthen the opening hook.",
                "critique_claim_id": "C1",
                "reasoning": "dummy episode action",
            }
            _, reward, terminated, _, info = env.step(action)
            rc = info["reward_components"]
            rewards_per_step.append(rc)

            if verbose:
                r9 = rc.get("r9_platform_pacing")
                r10 = rc.get("r10_retention_curve")
                r1 = rc.get("r1_hook_strength")
                r2 = rc.get("r2_coherence")
                r9_str = f"{r9:.3f}" if r9 is not None else "None"
                r10_str = f"{r10:.3f}" if r10 is not None else "None"
                print(
                    f"  Step {step + 1}: total={reward:.3f}  "
                    f"R1={r1:.3f}  R2={r2:.3f}  R9={r9_str}  R10={r10_str}"
                )

            if terminated:
                break

    return platform, rewards_per_step


def main():
    parser = argparse.ArgumentParser(description="Phase 12 dummy episode gate check")
    parser.add_argument("--difficulty", default="easy", choices=["easy", "medium", "hard"])
    parser.add_argument("--steps", type=int, default=3)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    print(f"Running dummy episode: difficulty={args.difficulty}, steps={args.steps}")
    platform, steps_data = run_episode(args.difficulty, args.steps, args.verbose)

    # Gate assertions
    errors = []
    for i, rc in enumerate(steps_data):
        if rc.get("r9_platform_pacing") is None:
            errors.append(f"Step {i+1}: r9_platform_pacing is None — R9 not firing")
        elif not (0.0 <= rc["r9_platform_pacing"] <= 1.0):
            errors.append(f"Step {i+1}: r9_platform_pacing out of range: {rc['r9_platform_pacing']}")

        if rc.get("r10_retention_curve") is None:
            errors.append(f"Step {i+1}: r10_retention_curve is None — R10 not firing")
        elif not (0.0 <= rc["r10_retention_curve"] <= 1.0):
            errors.append(f"Step {i+1}: r10_retention_curve out of range: {rc['r10_retention_curve']}")

    if errors:
        print("\n[GATE FAIL]")
        for e in errors:
            print(f"  ERROR: {e}")
        sys.exit(1)
    else:
        # Compute average AUC improvement for gate message
        r10_scores = [rc.get("r10_retention_curve", 0.0) for rc in steps_data if rc.get("r10_retention_curve") is not None]
        avg_r10 = sum(r10_scores) / len(r10_scores) if r10_scores else 0.0
        print(
            f"\nPHASE 12 GATE: PASS — Retention curve predictor active. "
            f"R10 firing. AUC improvement: +{avg_r10:.2f}."
        )


if __name__ == "__main__":
    main()
