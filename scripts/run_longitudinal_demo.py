"""
Phase 11 gate check — Longitudinal Episode Memory.

Simulates a creator returning for N consecutive sessions, showing how the
history buffer accumulates and how the Arbitrator's context changes.

Usage:
    python scripts/run_longitudinal_demo.py --creator S01 --sessions 6 --verbose
"""
import argparse
import sys
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from viral_script_engine.agents.critic import CritiqueClaim
from viral_script_engine.environment.env import ViralScriptEnv
from viral_script_engine.memory.history_store import HistoryStore

_ROOT = Path(__file__).parent.parent / "viral_script_engine"
_SCRIPTS_PATH = str(_ROOT / "data" / "test_scripts" / "scripts.json")
_CULTURAL_KB_PATH = str(_ROOT / "data" / "cultural_kb.json")


def _pick_action_from_session(session_num: int) -> dict:
    """Rotate actions so sessions show diverse behaviour."""
    actions = [
        {
            "action_type": "hook_rewrite",
            "target_section": "hook",
            "instruction": "Strengthen the opening hook with a direct claim.",
            "critique_claim_id": "C1",
            "reasoning": "Hook weakness is the dominant flaw.",
        },
        {
            "action_type": "cultural_ref_sub",
            "target_section": "body",
            "instruction": "Replace generic reference with regional cultural touchpoint.",
            "critique_claim_id": "C1",
            "reasoning": "Cultural mismatch detected — substituting references.",
        },
        {
            "action_type": "section_reorder",
            "target_section": "body",
            "instruction": "Move the strongest claim to the second sentence.",
            "critique_claim_id": "C1",
            "reasoning": "Coherence improved by reordering sections.",
        },
        {
            "action_type": "cta_placement",
            "target_section": "cta",
            "instruction": "Move CTA to the final 3 seconds.",
            "critique_claim_id": "C1",
            "reasoning": "CTA is misplaced — relocating to end.",
        },
    ]
    return actions[(session_num - 1) % len(actions)]


def _make_mock_critique(session_num: int):
    """Vary dominant flaw per session to simulate learning progression."""
    flaws = [
        "hook_weakness",
        "cultural_mismatch",
        "hook_weakness",
        "pacing_issue",
        "hook_weakness",
        "cta_weakness",
    ]
    flaw = flaws[(session_num - 1) % len(flaws)]
    real_claim = CritiqueClaim(
        claim_id="C1",
        severity="high",
        critique_class=flaw,
        claim_text=f"Test claim for {flaw}",
        evidence="evidence",
        timestamp_range="0-3s",
        is_falsifiable=True,
    )
    mock_critique = MagicMock()
    mock_critique.claims = [real_claim]
    mock_critique.overall_severity = "high"
    return mock_critique


def run_session(
    env: ViralScriptEnv,
    session_num: int,
    steps: int,
    verbose: bool,
    creator_id: str,
) -> dict:
    """Run one episode and return session summary."""
    # Always reset to the same script variety; override creator_id to track longitudinally
    obs, _ = env.reset(seed=42)
    env._current_creator_id = creator_id
    env._current_history_buffer = env.history_store.load(creator_id)

    # Rebuild obs so history fields reflect the correct creator
    if env._current_history_buffer is not None:
        obs["creator_history"] = env._current_history_buffer.model_dump()
        obs["history_context"] = env._current_history_buffer.to_prompt_context()
    else:
        obs["creator_history"] = None
        obs["history_context"] = None

    history_context = obs.get("history_context")
    history_present = history_context is not None

    if verbose:
        print(f"\nSESSION {session_num} ({'no history' if not history_present else str(session_num - 1) + ' session(s) history'})")
        if history_present:
            print(f"  History context:\n    " + history_context.replace("\n", "\n    "))

    mock_critique = _make_mock_critique(session_num)
    mock_defender = MagicMock()
    mock_defender.core_strength = "Strong cultural voice"
    mock_defender.core_strength_quote = "authentic reference"
    mock_defender.defense_argument = "Voice should be preserved"
    mock_defender.flagged_critic_claims = []
    mock_defender.regional_voice_elements = []
    mock_defender.model_dump.return_value = {
        "core_strength": "Strong cultural voice",
        "core_strength_quote": "authentic reference",
        "defense_argument": "Voice should be preserved",
        "flagged_critic_claims": [],
        "regional_voice_elements": [],
    }
    mock_rewrite = MagicMock()
    mock_rewrite.rewritten_script = obs["current_script"]
    mock_rewrite.diff = ""

    final_reward = 0.0
    action_taken = "none"

    with patch.object(env.critic, "critique", return_value=mock_critique), \
         patch.object(env.defender, "defend", return_value=mock_defender), \
         patch.object(env.rewriter, "rewrite", return_value=mock_rewrite):

        for step in range(steps):
            action = _pick_action_from_session(session_num)
            action_taken = action["action_type"]
            _, reward, terminated, _, info = env.step(action)
            final_reward = reward
            if terminated:
                break

    dominant_flaw = mock_critique.claims[0].critique_class

    if verbose:
        print(f"  Dominant flaw: {dominant_flaw}")
        print(f"  Action taken: {action_taken}")
        print(f"  Final reward: {final_reward:.2f}")

    return {
        "session": session_num,
        "dominant_flaw": dominant_flaw,
        "action_taken": action_taken,
        "final_reward": final_reward,
        "history_used": history_present,
    }


def main():
    parser = argparse.ArgumentParser(description="Phase 11 longitudinal memory gate check")
    parser.add_argument("--creator", default="S01", help="Creator ID (e.g. S01)")
    parser.add_argument("--sessions", type=int, default=6, help="Number of sessions to simulate")
    parser.add_argument("--steps", type=int, default=3, help="Steps per session")
    parser.add_argument("--verbose", action="store_true", help="Print session details")
    args = parser.parse_args()

    # Use a temp dir for histories so tests don't pollute production data
    history_dir = str(
        Path(__file__).parent.parent / "viral_script_engine" / "data" / "creator_histories"
    )
    os.makedirs(history_dir, exist_ok=True)

    env = ViralScriptEnv(
        scripts_path=_SCRIPTS_PATH,
        cultural_kb_path=_CULTURAL_KB_PATH,
        difficulty="easy",
        use_escalation=False,
        use_anti_gaming=False,
        max_steps=args.steps,  # ensure episode terminates within the demo step count
    )
    # Override store_dir to our directory
    env.history_store = HistoryStore(store_dir=history_dir)

    results = []
    for session_num in range(1, args.sessions + 1):
        summary = run_session(
            env=env,
            session_num=session_num,
            steps=args.steps,
            verbose=args.verbose,
            creator_id=args.creator,
        )
        results.append(summary)

    # Verify history files exist
    store = HistoryStore(store_dir=history_dir)
    creators = store.list_creators()

    rewards = [r["final_reward"] for r in results]
    rewards_str = " -> ".join(f"{r:.2f}" for r in rewards)

    # Determine trend from final buffer
    final_buffer = store.load(args.creator)
    trend = final_buffer.improvement_trend if final_buffer else "unknown"
    sessions_with_history = sum(1 for r in results if r["history_used"])

    print(f"\nPROGRESSION SUMMARY:")
    print(f"  Rewards: {rewards_str}")
    print(f"  Trend: {trend}")
    print(f"  Sessions using history: {sessions_with_history} of {args.sessions}")
    print(f"  History files saved: {len(creators)} creator(s) in {history_dir}")

    # Gate checks
    errors = []
    if len(results) != args.sessions:
        errors.append(f"Expected {args.sessions} sessions, got {len(results)}")
    if sessions_with_history < args.sessions - 1:
        errors.append(
            f"History not being used: only {sessions_with_history} sessions had history "
            f"(expected {args.sessions - 1} after the first)"
        )
    if args.creator not in creators:
        errors.append(f"History file for creator '{args.creator}' not found in {history_dir}")
    if final_buffer is None:
        errors.append("Final history buffer could not be loaded")
    else:
        if final_buffer.total_episodes != args.sessions:
            errors.append(
                f"total_episodes={final_buffer.total_episodes}, expected {args.sessions}"
            )
        if len(final_buffer.recent_episodes) > 5:
            errors.append(
                f"Sliding window not working: {len(final_buffer.recent_episodes)} episodes (max 5)"
            )

    if errors:
        print("\n[GATE FAIL]")
        for e in errors:
            print(f"  ERROR: {e}")
        sys.exit(1)

    print(
        f"\nPHASE 11 GATE: PASS — Longitudinal memory active. "
        f"{args.sessions} sessions completed. Final reward trend: {trend}."
    )


if __name__ == "__main__":
    main()
