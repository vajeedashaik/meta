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


def _bar(score: float, width: int = 8) -> str:
    filled = round(score * width)
    return "#" * filled + "." * (width - filled)


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
        title="[bold blue]Phase 6 Demo Episode[/bold blue]",
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
        mod_out = info.get("moderation_output", {})
        orig_out = info.get("originality_output", {})

        if verbose:
            t = Table(title=f"Step {step_num + 1} — {action_type.value}", box=box.SIMPLE_HEAD)
            t.add_column("Metric", style="cyan", min_width=22)
            t.add_column("Score", min_width=12)
            t.add_column("Bar", min_width=10)

            def _row(label, key, suffix=""):
                val = rc.get(key)
                score_str = f"{val:.3f}" if val is not None else "N/A"
                bar_str = _bar(val) if val is not None else ""
                t.add_row(label, score_str + suffix, bar_str)

            _row("R1 Hook Strength", "r1_hook_strength")
            _row("R2 Coherence", "r2_coherence")
            _row("R3 Cultural", "r3_cultural_alignment")
            _row("R4 Resolution", "r4_debate_resolution")
            _row("R5 Preservation", "r5_defender_preservation")

            r6_val = rc.get("r6_safety")
            r6_suffix = "  [OK] No flags" if mod_out.get("total_flags", 0) == 0 else f"  [!] {mod_out.get('total_flags', 0)} flag(s)"
            r6_str = (f"{r6_val:.3f}{r6_suffix}" if r6_val is not None else "N/A")
            t.add_row("R6 Safety", r6_str, _bar(r6_val) if r6_val is not None else "")

            r7_val = rc.get("r7_originality")
            orig_flags = len(orig_out.get("flags", []))
            r7_suffix = f"  [!] {orig_flags} template match(es)" if orig_flags > 0 else "  [OK] Original"
            r7_str = (f"{r7_val:.3f}{r7_suffix}" if r7_val is not None else "N/A")
            t.add_row("R7 Originality", r7_str, _bar(r7_val) if r7_val is not None else "")

            t.add_row("-" * 22, "-" * 12, "-" * 10)
            t.add_row("[bold]Total[/bold]", f"[bold]{reward:.3f}[/bold]", _bar(reward))

            if info.get("anti_gaming_triggered"):
                t.add_row("Anti-Gaming Penalty", f"[red]{rc.get('anti_gaming_penalty', 0):.3f}[/red]", "")
                t.add_row("Penalty Reason", f"[red]{info.get('penalty_reason', '')}[/red]", "")
            t.add_row("Terminated", str(terminated), "")
            console.print(t)

            # Show moderation flags in red panel if any
            mod_flags = mod_out.get("flags", [])
            if mod_flags:
                flag_lines = []
                for fl in mod_flags:
                    flag_lines.append(
                        f"  [{fl['severity']}] {fl['category']} in {fl['position']}: \"{fl['trigger_phrase']}\" → {fl['suggestion']}"
                    )
                console.print(Panel(
                    "\n".join(flag_lines),
                    title="[bold red]!! MODERATION FLAGS DETECTED[/bold red]",
                    border_style="red",
                ))

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
            "moderation_output": mod_out,
            "originality_output": orig_out,
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
        f"R1 Hook Strength:    {final_rc.get('r1_hook_strength', 'N/A')}\n"
        f"R2 Coherence:        {final_rc.get('r2_coherence', 'N/A')}\n"
        f"R6 Safety:           {final_rc.get('r6_safety', 'N/A')}\n"
        f"R7 Originality:      {final_rc.get('r7_originality', 'N/A')}\n"
        f"Steps completed: {final_state['step_num']}",
        title="Episode Summary",
        border_style="green",
    ))

    return episode_log


def main():
    parser = argparse.ArgumentParser(description="Run Phase 6 dummy episode")
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
        final_rc.get("r6_safety") is not None
        and final_rc.get("r7_originality") is not None
        and log_path.exists()
    )
    style = "bold green" if gate_pass else "bold red"
    if gate_pass:
        label = "PHASE 6 GATE: PASS — R6 (safety) and R7 (originality) active. Total reward components: 7."
    else:
        label = "PHASE 6 GATE: FAIL — R6 or R7 missing from reward output."
    console.print(Panel(f"[{style}]{label}[/{style}]", border_style="green" if gate_pass else "red"))


if __name__ == "__main__":
    main()
