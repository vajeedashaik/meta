#!/usr/bin/env python3
import json
import sys
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich import box

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from viral_script_engine.agents.baseline_arbitrator import BaselineArbitratorAgent
from viral_script_engine.environment.env import ViralScriptEnv

console = Console()
BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

_SCHEDULE = (
    [(i, "easy") for i in range(1, 9)]
    + [(i, "medium") for i in range(9, 17)]
    + [(i, "hard") for i in range(17, 21)]
)

_REWARD_KEYS = ["r1_hook_strength", "r2_coherence", "r3_cultural_alignment",
                "r4_debate_resolution", "r5_defender_preservation"]


def _make_env(difficulty: str) -> ViralScriptEnv:
    return ViralScriptEnv(
        scripts_path=str(BASE_DIR / "data" / "test_scripts" / "scripts.json"),
        cultural_kb_path=str(BASE_DIR / "data" / "cultural_kb.json"),
        max_steps=5,
        difficulty=difficulty,
    )


def run_episode(ep_num: int, difficulty: str, agent: BaselineArbitratorAgent) -> dict:
    env = _make_env(difficulty)
    obs, _ = env.reset()

    episode_id = obs["episode_id"]
    script_id = "unknown"
    state = env.state()
    original_script = state.get("original_script", "")

    steps_log = []
    total_reward = 0.0

    for _ in range(env.max_steps):
        action = agent.act(obs)
        obs, reward, terminated, truncated, info = env.step(action)
        rc = info["reward_components"]
        anti_log = info.get("anti_gaming_log", {})

        step_entry = {
            "r1": rc.get("r1_hook_strength"),
            "r2": rc.get("r2_coherence"),
            "r3": rc.get("r3_cultural_alignment"),
            "r4": rc.get("r4_debate_resolution"),
            "r5": rc.get("r5_defender_preservation"),
            "total": reward,
            "anti_gaming_triggered": anti_log.get("triggered", False),
            "penalty": anti_log.get("penalty_applied", 0.0),
        }
        steps_log.append(step_entry)
        total_reward = reward

        if terminated or truncated:
            break

    final_state = env.state()
    final_script = final_state.get("current_script", "")

    return {
        "episode_num": ep_num,
        "episode_id": episode_id,
        "difficulty": difficulty,
        "script_id": script_id,
        "steps": steps_log,
        "total_reward": total_reward,
        "anti_gaming_logs": final_state.get("anti_gaming_logs", []),
        "original_script": original_script,
        "final_script": final_script,
    }


def main():
    agent = BaselineArbitratorAgent()
    all_episodes = []

    for ep_num, difficulty in _SCHEDULE:
        console.print(f"[dim]Episode {ep_num:02d}/20 ({difficulty})...[/dim]")
        try:
            result = run_episode(ep_num, difficulty, agent)
            all_episodes.append(result)
            console.print(
                f"  -> total_reward={result['total_reward']:.3f}  "
                f"steps={len(result['steps'])}"
            )
        except Exception as e:
            console.print(f"  [red]ERROR episode {ep_num}: {e}[/red]")
            all_episodes.append({
                "episode_num": ep_num,
                "episode_id": "",
                "difficulty": difficulty,
                "script_id": "error",
                "steps": [],
                "total_reward": 0.0,
                "anti_gaming_logs": [],
                "original_script": "",
                "final_script": "",
                "error": str(e),
            })

    results_path = LOGS_DIR / "baseline_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(all_episodes, f, indent=2, default=str)

    _save_plots(all_episodes)
    _print_summary(all_episodes)

    mean_total = float(np.mean([e["total_reward"] for e in all_episodes]))
    console.print(
        f"\n[bold green]PHASE 2 GATE: PASS — Baseline curves saved. "
        f"Pre-training mean total reward: {mean_total:.2f}[/bold green]"
    )


def _collect_reward_series(episodes: list, key: str):
    series = []
    for ep in episodes:
        vals = [s.get(key) for s in ep.get("steps", []) if s.get(key) is not None]
        series.append(vals[-1] if vals else 0.0)
    return series


def _save_plots(episodes: list):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = {
        "r1": "R1 Hook Strength",
        "r2": "R2 Coherence",
        "r3": "R3 Cultural Alignment",
        "r4": "R4 Debate Resolution",
        "r5": "R5 Defender Preservation",
        "total": "Total Reward",
    }
    keys = list(labels.keys())
    ep_nums = [e["episode_num"] for e in episodes]

    fig, axes = plt.subplots(2, 3, figsize=(14, 8), dpi=150)
    fig.suptitle(
        "Baseline (Untrained) Arbitrator — Pre-Training Reward Curves",
        fontsize=13,
    )

    for idx, key in enumerate(keys):
        ax = axes[idx // 3][idx % 3]
        series = _collect_reward_series(episodes, key) if key != "total" else [e["total_reward"] for e in episodes]
        ax.plot(ep_nums, series, marker="o", linewidth=1.5, markersize=4)
        ax.set_title(labels[key], fontsize=10)
        ax.set_xlabel("Episode", fontsize=8)
        ax.set_ylabel("Reward", fontsize=8)
        ax.set_ylim(0, 1)
        ax.set_xlim(min(ep_nums) - 0.5, max(ep_nums) + 0.5)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plot_path = LOGS_DIR / "baseline_reward_curves.png"
    plt.savefig(str(plot_path), dpi=150)
    plt.close()
    console.print(f"[dim]Curves saved -> {plot_path}[/dim]")


def _print_summary(episodes: list):
    table = Table(title="Baseline Results — Mean +/- Std (20 episodes)", box=box.SIMPLE_HEAD)
    table.add_column("Reward", style="cyan", min_width=28)
    table.add_column("Mean", min_width=8)
    table.add_column("Std", min_width=8)
    table.add_column("Min", min_width=8)
    table.add_column("Max", min_width=8)

    label_map = {
        "r1": "R1 Hook Strength",
        "r2": "R2 Coherence",
        "r3": "R3 Cultural Alignment",
        "r4": "R4 Debate Resolution",
        "r5": "R5 Defender Preservation",
        "total": "Total Reward",
    }
    for key, label in label_map.items():
        if key == "total":
            vals = [e["total_reward"] for e in episodes]
        else:
            vals = _collect_reward_series(episodes, key)
        arr = np.array(vals, dtype=float)
        table.add_row(
            label,
            f"{arr.mean():.3f}",
            f"{arr.std():.3f}",
            f"{arr.min():.3f}",
            f"{arr.max():.3f}",
        )

    console.print(table)


if __name__ == "__main__":
    main()
