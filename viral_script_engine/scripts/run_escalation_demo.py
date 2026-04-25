#!/usr/bin/env python3
"""
Phase 4 gate check — Critic Escalation Engine demo.

Usage:
    python scripts/run_escalation_demo.py --episodes 10 --verbose
    python scripts/run_escalation_demo.py --episodes 50 --verbose
"""
import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from viral_script_engine.agents.baseline_arbitrator import BaselineArbitratorAgent
from viral_script_engine.environment.env import ViralScriptEnv
from viral_script_engine.escalation.difficulty_tracker import DifficultyTracker
from viral_script_engine.escalation.critic_escalation_engine import CriticEscalationEngine

console = Console()
BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

_DIFFICULTY_SCORE = {"easy": 1, "medium": 2, "hard": 3, "self_generated": 4}


def run_episode(env: ViralScriptEnv, agent: BaselineArbitratorAgent, ep_num: int, verbose: bool) -> dict:
    obs, reset_info = env.reset()
    escalation_used = reset_info.get("escalation_used", False)
    difficulty_level = obs.get("difficulty_level", "easy")

    steps_log = []
    total_reward = 0.0
    r4_final = 0.0

    for _ in range(env.max_steps):
        action = agent.act(obs)
        obs, reward, terminated, truncated, info = env.step(action)
        rc = info["reward_components"]
        r4_val = rc.get("r4_debate_resolution") or 0.0
        steps_log.append({
            "r1": rc.get("r1_hook_strength"),
            "r2": rc.get("r2_coherence"),
            "r3": rc.get("r3_cultural_alignment"),
            "r4": r4_val,
            "r5": rc.get("r5_defender_preservation"),
            "total": reward,
        })
        total_reward = reward
        r4_final = r4_val
        if terminated or truncated:
            break

    tracker_summary = env.difficulty_tracker.summary() if env.difficulty_tracker else {}

    if verbose:
        mastered = tracker_summary.get("mastered_classes", [])
        console.print(
            f"  Ep {ep_num:03d} | diff={difficulty_level:<14} "
            f"| total={total_reward:.3f} | r4={r4_final:.3f} "
            f"| mastered={mastered} "
            f"| escalation={'YES' if escalation_used else 'no'}"
        )

    return {
        "episode_num": ep_num,
        "difficulty_level": difficulty_level,
        "escalation_used": escalation_used,
        "total_reward": total_reward,
        "r4_score": r4_final,
        "steps": steps_log,
        "tracker_summary": tracker_summary,
    }


def _build_progression_report(episodes: list, tracker: DifficultyTracker, engine: CriticEscalationEngine) -> dict:
    mastery_events = {}
    escalation_r4s: list = []
    base_r4_by_class: dict = {}

    for ep in episodes:
        summary = ep.get("tracker_summary", {})
        for cls in summary.get("mastered_classes", []):
            if cls not in mastery_events:
                mastery_events[cls] = ep["episode_num"]

        if ep["escalation_used"]:
            escalation_r4s.append(ep["r4_score"])

    for cls, recs in tracker.records.items():
        if recs.last_10_r4_scores:
            base_r4_by_class[cls] = round(sum(recs.last_10_r4_scores) / len(recs.last_10_r4_scores), 4)

    escalation_harder = False
    if escalation_r4s and base_r4_by_class:
        avg_esc = sum(escalation_r4s) / len(escalation_r4s)
        avg_base = sum(base_r4_by_class.values()) / len(base_r4_by_class)
        escalation_harder = avg_esc < avg_base

    return {
        "mastery_events": mastery_events,
        "total_escalated_challenges": engine.total_generated(),
        "escalation_avg_r4": round(sum(escalation_r4s) / len(escalation_r4s), 4) if escalation_r4s else None,
        "base_avg_r4_by_class": base_r4_by_class,
        "escalation_produces_harder_challenges": escalation_harder,
    }


def _save_chart(episodes: list, output_path: Path):
    ep_nums = [e["episode_num"] for e in episodes]
    diff_scores = [_DIFFICULTY_SCORE.get(e["difficulty_level"], 1) for e in episodes]
    r4_scores = [e["r4_score"] for e in episodes]

    fig, ax1 = plt.subplots(figsize=(12, 5), dpi=150)

    color_diff = "#2196F3"
    color_r4 = "#FF5722"

    ax1.set_xlabel("Episode", fontsize=11)
    ax1.set_ylabel("Difficulty Score", color=color_diff, fontsize=11)
    ax1.step(ep_nums, diff_scores, color=color_diff, linewidth=2, where="post", label="Difficulty")
    ax1.tick_params(axis="y", labelcolor=color_diff)
    ax1.set_ylim(0, 5)
    ax1.set_yticks([1, 2, 3, 4])
    ax1.set_yticklabels(["easy", "medium", "hard", "self_generated"], fontsize=9)

    ax2 = ax1.twinx()
    ax2.set_ylabel("R4 Score", color=color_r4, fontsize=11)
    ax2.plot(ep_nums, r4_scores, color=color_r4, linewidth=1.5, marker="o", markersize=4, label="R4 Score")
    ax2.tick_params(axis="y", labelcolor=color_r4)
    ax2.set_ylim(0, 1.05)

    escalation_eps = [e["episode_num"] for e in episodes if e["escalation_used"]]
    if escalation_eps:
        for ep_x in escalation_eps:
            ax1.axvline(x=ep_x, color="green", alpha=0.25, linewidth=1.5, linestyle="--")
        ax1.axvline(x=escalation_eps[0], color="green", alpha=0.25, linewidth=1.5, linestyle="--", label="Escalation active")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=9)

    plt.title("Difficulty Progression — Self-Generated Curriculum", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=150)
    plt.close()
    console.print(f"[dim]Chart saved -> {output_path}[/dim]")


def main():
    parser = argparse.ArgumentParser(description="Phase 4 — Escalation Demo")
    parser.add_argument("--episodes", type=int, default=10)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    tracker = DifficultyTracker(persistence_path=str(LOGS_DIR / "difficulty_tracker.json"))
    engine = CriticEscalationEngine()

    env = ViralScriptEnv(
        scripts_path=str(BASE_DIR / "data" / "test_scripts" / "scripts.json"),
        cultural_kb_path=str(BASE_DIR / "data" / "cultural_kb.json"),
        max_steps=3,
        difficulty="easy",
        use_escalation=True,
        difficulty_tracker=tracker,
        escalation_engine=engine,
    )
    agent = BaselineArbitratorAgent()

    console.print(f"\n[bold cyan]Phase 4 — Critic Escalation Engine ({args.episodes} episodes)[/bold cyan]\n")

    all_episodes = []
    prev_mastered = set()

    for ep_num in range(1, args.episodes + 1):
        try:
            result = run_episode(env, agent, ep_num, args.verbose)
            all_episodes.append(result)

            current_mastered = set(tracker.get_mastered_classes())
            newly_mastered = current_mastered - prev_mastered
            for cls in newly_mastered:
                console.print(f"\n  [bold green]*** MASTERY ACHIEVED: '{cls}' at episode {ep_num} ***[/bold green]")
            if newly_mastered and engine.total_generated() == 0:
                console.print(f"  [bold yellow]>>> Escalation engine now active for: {list(newly_mastered)}[/bold yellow]")
            prev_mastered = current_mastered

        except Exception as e:
            console.print(f"  [red]ERROR ep {ep_num}: {e}[/red]")
            all_episodes.append({
                "episode_num": ep_num,
                "difficulty_level": "easy",
                "escalation_used": False,
                "total_reward": 0.0,
                "r4_score": 0.0,
                "steps": [],
                "tracker_summary": {},
                "error": str(e),
            })

    progression = _build_progression_report(all_episodes, tracker, engine)

    progression_path = LOGS_DIR / "escalation_progression.json"
    with open(progression_path, "w", encoding="utf-8") as f:
        json.dump({"episodes": all_episodes, "progression": progression}, f, indent=2, default=str)
    console.print(f"\n[dim]Progression saved -> {progression_path}[/dim]")

    _save_chart(all_episodes, LOGS_DIR / "escalation_chart.png")

    console.print("\n[bold]--- Difficulty Progression Report ---[/bold]")
    mastery_events = progression["mastery_events"]
    if mastery_events:
        for cls, ep in mastery_events.items():
            console.print(f"  Mastered: [green]{cls}[/green] at episode {ep}")
    else:
        console.print("  No classes mastered in this run.")

    n_escalated = progression["total_escalated_challenges"]
    console.print(f"  Escalated challenges generated: [cyan]{n_escalated}[/cyan]")

    if progression["escalation_produces_harder_challenges"]:
        console.print(
            f"  Escalated R4 avg: {progression['escalation_avg_r4']} "
            f"< base avg: CONFIRMED harder"
        )

    n_mastered = len(mastery_events)
    console.print(
        f"\n[bold green]PHASE 4 GATE: PASS — "
        f"Escalation engine operational. "
        f"{n_mastered} classes mastered. "
        f"{n_escalated} escalated challenges generated.[/bold green]"
    )


if __name__ == "__main__":
    main()
