#!/usr/bin/env python3
import argparse
import json
import random
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from viral_script_engine.environment.actions import ActionType
from viral_script_engine.environment.env import ViralScriptEnv

console = Console()
BASE_DIR = Path(__file__).parent.parent


def build_random_action(action_type: ActionType) -> dict:
    labels = {
        ActionType.HOOK_REWRITE: ("hook", "Rewrite the hook to open with a specific number or bold claim."),
        ActionType.SECTION_REORDER: ("body", "Move the strongest point to immediately follow the hook."),
        ActionType.CULTURAL_REF_SUB: ("full", "Replace any generic references with locally relevant ones."),
        ActionType.CTA_PLACEMENT: ("cta", "Move the call-to-action earlier, before the 80% mark."),
    }
    section, instruction = labels[action_type]
    return {
        "action_type": action_type.value,
        "target_section": section,
        "instruction": instruction,
        "critique_claim_id": "C1",
        "reasoning": f"Demo run: applying {action_type.value}",
    }


def run_episode(difficulty: str, steps: int, verbose: bool) -> dict:
    scripts_path = str(BASE_DIR / "data" / "test_scripts" / "scripts.json")
    env = ViralScriptEnv(scripts_path=scripts_path, max_steps=steps, difficulty=difficulty)

    obs, _ = env.reset()
    console.print(Panel(
        f"[bold]Episode started[/bold]\n"
        f"Difficulty: {difficulty}  |  Max steps: {steps}\n"
        f"Region: {obs['region']}  |  Platform: {obs['platform']}  |  Niche: {obs['niche']}\n"
        f"Episode ID: {obs['episode_id']}",
        title="[bold blue]Phase 1 Demo Episode[/bold blue]",
        border_style="blue",
    ))

    episode_log = {
        "episode_id": obs["episode_id"],
        "difficulty": difficulty,
        "steps": [],
        "final_state": None,
    }

    for step_num in range(steps):
        action_type = random.choice(list(ActionType))
        action = build_random_action(action_type)

        obs, reward, terminated, truncated, info = env.step(action)
        rc = info["reward_components"]

        if verbose:
            t = Table(title=f"Step {step_num + 1} — {action_type.value}", box=box.SIMPLE_HEAD)
            t.add_column("Metric", style="cyan", min_width=22)
            t.add_column("Value", min_width=12)
            r1_val = rc.get("r1_hook_strength")
            r2_val = rc.get("r2_coherence")
            t.add_row("R1 Hook Strength", f"{r1_val:.3f}" if r1_val is not None else "N/A")
            t.add_row("R2 Coherence", f"{r2_val:.3f}" if r2_val is not None else "N/A")
            t.add_row("Total Reward", f"[bold]{reward:.3f}[/bold]")
            if info.get("anti_gaming_triggered"):
                t.add_row("Anti-Gaming Penalty", f"[red]{rc.get('anti_gaming_penalty', 0):.3f}[/red]")
                t.add_row("Penalty Reason", f"[red]{info.get('penalty_reason', '')}[/red]")
            t.add_row("Terminated", str(terminated))
            console.print(t)

            if obs.get("debate_history"):
                latest = obs["debate_history"][-1]
                if latest.get("rewrite_diff"):
                    console.print(Panel(
                        latest["rewrite_diff"][:600] or "(no diff)",
                        title="Script Diff",
                        border_style="yellow",
                    ))

        episode_log["steps"].append({
            "step": step_num + 1,
            "action": action,
            "reward": reward,
            "reward_components": rc,
            "anti_gaming": info.get("anti_gaming_triggered", False),
            "terminated": terminated,
        })

        if terminated:
            break

    final_state = env.state()
    episode_log["final_state"] = final_state
    final_rc = final_state["reward_components"]

    console.print(Panel(
        f"[bold green]Final Reward:[/bold green] {final_rc.get('total', 0):.3f}\n"
        f"R1 Hook Strength: {final_rc.get('r1_hook_strength', 'N/A')}\n"
        f"R2 Coherence: {final_rc.get('r2_coherence', 'N/A')}\n"
        f"Steps completed: {final_state['step_num']}",
        title="Episode Summary",
        border_style="green",
    ))

    return episode_log


def main():
    parser = argparse.ArgumentParser(description="Run Phase 1 dummy episode")
    parser.add_argument("--difficulty", default="easy", choices=["easy", "medium", "hard"])
    parser.add_argument("--steps", type=int, default=3)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    episode_log = run_episode(args.difficulty, args.steps, args.verbose)

    logs_dir = BASE_DIR / "logs"
    logs_dir.mkdir(exist_ok=True)
    log_path = logs_dir / f"episode_{episode_log['episode_id']}.json"
    with open(log_path, "w") as f:
        json.dump(episode_log, f, indent=2, default=str)
    console.print(f"[dim]Episode log saved -> {log_path}[/dim]")

    final_rc = episode_log["final_state"]["reward_components"]
    gate_pass = (
        final_rc.get("r1_hook_strength") is not None
        and final_rc.get("r2_coherence") is not None
        and log_path.exists()
    )
    style = "bold green" if gate_pass else "bold red"
    label = f"PHASE 1 GATE: {'PASS' if gate_pass else 'FAIL'}"
    console.print(Panel(f"[{style}]{label}[/{style}]", border_style="green" if gate_pass else "red"))


if __name__ == "__main__":
    main()
