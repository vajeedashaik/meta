"""
A/B Episode Runner — Phase 10 Gate Check Script

Usage:
    python scripts/run_ab_episode.py --script S08 --steps 4 --verbose
    python scripts/run_ab_episode.py --script S03 --steps 3
"""
import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env", override=False)

from viral_script_engine.environment.ab_env import ABScriptEnv
from viral_script_engine.rewards.contrastive_reward import ContrastiveReward
from viral_script_engine.agents.baseline_arbitrator import BaselineArbitratorAgent

_ROOT = Path(__file__).parent.parent
_SCRIPTS_PATH = str(_ROOT / "data" / "test_scripts" / "scripts.json")
_CULTURAL_KB_PATH = str(_ROOT / "data" / "cultural_kb.json")

_DIFFICULTY_FOR_SCRIPT = {
    "S01": "easy", "S02": "easy", "S03": "easy", "S04": "easy",
    "S05": "medium", "S06": "medium", "S07": "medium",
    "S08": "hard", "S09": "hard", "S10": "hard",
}

SEP = "═" * 70


def _rc_row(label: str, before: float, after: float) -> str:
    delta = after - before
    sign = "+" if delta >= 0 else ""
    warn = " ⚠" if delta < -0.05 else ""
    return f"  {label}: {before:.2f} → {after:.2f} ({sign}{delta:.2f}){warn}"


def _traj_summary(traj: dict, label: str) -> str:
    rc = traj.get("reward_components") or {}
    r1 = rc.get("r1_hook_strength") or 0.0
    r3 = rc.get("r3_cultural_alignment") or 0.0
    total = rc.get("total") or traj.get("cumulative_reward", 0.0)
    return (
        f"  [{label}] script[:60]: {traj.get('current_script', '')[:60]!r}\n"
        f"  R1={r1:.2f}  R3={r3:.2f}  Cumulative={traj.get('cumulative_reward', 0.0):.3f}"
    )


def run_ab_episode(script_id: str, num_steps: int, verbose: bool):
    difficulty = _DIFFICULTY_FOR_SCRIPT.get(script_id, "hard")
    ab_env = ABScriptEnv(
        scripts_path=_SCRIPTS_PATH,
        cultural_kb_path=_CULTURAL_KB_PATH,
        max_steps=num_steps + 1,  # +1 because step 1 is forced
        difficulty=difficulty,
    )
    arbitrator = BaselineArbitratorAgent()

    print(f"\n{SEP}")
    print(f"  A/B EPISODE — Script: {script_id}  Steps: {num_steps}  Difficulty: {difficulty}")
    print(SEP)

    # Reset — forced step 1 runs automatically
    state = ab_env.reset_from_script_id(script_id, _SCRIPTS_PATH)

    traj_a = state["trajectory_a"]
    traj_b = state["trajectory_b"]
    forced_a = ab_env._forced_action_a
    forced_b = ab_env._forced_action_b

    print(f"\n{SEP}")
    print("  STEP 1 (FORCED)")
    print(SEP)
    col_w = 34
    print(
        f"  {'TRAJECTORY A (Critic-first)':<{col_w}}"
        f"  {'TRAJECTORY B (Defender-first)'}"
    )
    print(
        f"  Action: {forced_a.get('action_type','?'):<{col_w-8}}"
        f"  Action: {forced_b.get('action_type','?')}"
    )
    print(
        f"  Cumulative: {traj_a['cumulative_reward']:.3f}{'':<{col_w-20}}"
        f"  Cumulative: {traj_b['cumulative_reward']:.3f}"
    )
    if verbose:
        print(f"  Reasoning A: {forced_a.get('reasoning','')[:60]}")
        print(f"  Reasoning B: {forced_b.get('reasoning','')[:60]}")

    print(f"\n  Delta after step 1: {state['delta']:+.3f}  (leading: Trajectory {state['leading_trajectory']})")

    # Free steps (2+)
    for step_idx in range(2, num_steps + 1):
        if traj_a.get("terminated") and traj_b.get("terminated"):
            break

        # Arbitrator acts based on current trajectory_a state (simplification for demo)
        obs_for_arb = {
            "current_script": traj_a.get("current_script", ""),
            "debate_history": traj_a.get("debate_history", []),
            "reward_components": traj_a.get("reward_components", {}),
        }
        action = arbitrator.act(obs_for_arb)

        print(f"\n{SEP}")
        print(f"  STEP {step_idx} (FREE CHOICE)")
        print(SEP)
        print(f"  Arbitrator action: {action.get('action_type')} → {action.get('critique_claim_id')}")

        prev_a_cum = traj_a["cumulative_reward"]
        prev_b_cum = traj_b["cumulative_reward"]

        state, ep_reward, terminated, _, _ = ab_env.step(action)
        traj_a = state["trajectory_a"]
        traj_b = state["trajectory_b"]

        print(
            f"  Traj A cumulative: {prev_a_cum:.3f} → {traj_a['cumulative_reward']:.3f}"
            f"  ({traj_a['cumulative_reward'] - prev_a_cum:+.3f})"
        )
        print(
            f"  Traj B cumulative: {prev_b_cum:.3f} → {traj_b['cumulative_reward']:.3f}"
            f"  ({traj_b['cumulative_reward'] - prev_b_cum:+.3f})"
        )
        print(f"  Delta: {state['delta']:+.3f}  Leading: Trajectory {state['leading_trajectory']}")

        if terminated:
            break

    # Episode end
    traj_a_final = state["trajectory_a"]
    traj_b_final = state["trajectory_b"]
    final_delta = state["delta"]

    contrastive = ab_env.contrastive_reward_calc.compute(
        ab_env._traj_a, ab_env._traj_b
    )

    winner_label = {
        "A": "A (critic-first was better)",
        "B": "B (defender-first was better)",
        "tie": "tie",
    }.get(contrastive.winning_trajectory, contrastive.winning_trajectory)

    lesson_map = {
        "critic_first": "Act on the Critic's top severity claim first to maximise early gains.",
        "defender_first": "On scripts with strong core voice, preserve the Defender's concern first.",
        "tie": "Both orderings performed similarly — action choice matters more than sequence.",
    }
    lesson = lesson_map.get(contrastive.winning_trajectory_type, "")

    print(f"\n{SEP}")
    print("  EPISODE END")
    print(SEP)
    print(f"  Trajectory A final cumulative:  {traj_a_final['cumulative_reward']:.3f}")
    print(f"  Trajectory B final cumulative:  {traj_b_final['cumulative_reward']:.3f}")
    print(f"  Winner: {winner_label}")
    print(f"  Delta:  {final_delta:+.3f}")
    print(f"  Base reward:      {contrastive.base_reward:.4f}")
    print(f"  Contrast bonus:   {contrastive.contrast_bonus:+.4f}")
    print(f"  Contrastive reward: {contrastive.final_reward:.4f}")
    print(f"  Lesson: {lesson}")
    print()

    gate_pass = (
        abs(final_delta) > 1e-6
        and 0.0 <= contrastive.final_reward <= 1.0
    )
    if gate_pass:
        print(
            f"PHASE 10 GATE: PASS — A/B environment running. "
            f"Contrastive reward active. Delta: {final_delta:.3f}."
        )
    else:
        print(
            f"PHASE 10 GATE: FAIL — delta={final_delta:.6f}, "
            f"reward={contrastive.final_reward:.4f}"
        )
        sys.exit(1)

    return contrastive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run an A/B episode (Phase 10)")
    parser.add_argument("--script", default="S08", help="Script ID (default: S08)")
    parser.add_argument("--steps", type=int, default=4, help="Total steps including forced step 1")
    parser.add_argument("--verbose", action="store_true", help="Show reasoning details")
    args = parser.parse_args()

    run_ab_episode(args.script, args.steps, args.verbose)
