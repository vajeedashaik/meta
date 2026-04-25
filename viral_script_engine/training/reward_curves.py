"""
Judge-facing comparison plot: Trained vs Untrained Arbitrator.
Layout: 2 rows × 3 cols (R1, R2, R3, R4, R5, Total)

Usage:
  from viral_script_engine.training.reward_curves import plot_training_curves
  plot_training_curves()
"""
import json
from pathlib import Path
from typing import Optional


_REWARD_LABELS = {
    "r1": "R1 Hook Strength",
    "r2": "R2 Coherence",
    "r3": "R3 Cultural Alignment",
    "r4": "R4 Debate Resolution",
    "r5": "R5 Defender Preservation",
    "total": "Total Reward",
}

_REWARD_KEYS = ["r1", "r2", "r3", "r4", "r5", "total"]


def _collect_final_rewards(episodes: list, key: str) -> list:
    series = []
    for ep in episodes:
        if key == "total":
            series.append(ep.get("total_reward", 0.0))
        else:
            steps = ep.get("steps", [])
            vals = [s.get(key) for s in steps if s.get(key) is not None]
            series.append(vals[-1] if vals else 0.0)
    return series


def _load_json(path: str) -> list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def plot_training_curves(
    baseline_log_path: str = "logs/baseline_results.json",
    training_log_path: Optional[str] = "logs/training_results.json",
    output_path: str = "logs/training_vs_baseline.png",
):
    """
    Judge-facing comparison plot.
    Layout: 2 rows × 3 cols (R1, R2, R3, R4, R5, Total)

    Per subplot:
    - Grey line: baseline reward per episode
    - Blue line: trained reward per episode (if available)
    - Horizontal dashed line: baseline mean

    Saves PNG (dpi=150) and PDF. Prints improvement summary.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    baseline = _load_json(baseline_log_path)
    has_trained = training_log_path and Path(training_log_path).exists()
    trained = _load_json(training_log_path) if has_trained else None

    ep_nums_base = list(range(1, len(baseline) + 1))
    ep_nums_train = list(range(1, len(trained) + 1)) if trained else []

    fig, axes = plt.subplots(2, 3, figsize=(14, 8), dpi=150)
    fig.suptitle(
        "Trained vs Untrained Arbitrator — Reward Improvement",
        fontsize=13,
        fontweight="bold",
    )

    for idx, key in enumerate(_REWARD_KEYS):
        ax = axes[idx // 3][idx % 3]
        label = _REWARD_LABELS[key]

        base_series = _collect_final_rewards(baseline, key)
        base_mean = float(np.mean(base_series)) if base_series else 0.0

        ax.plot(ep_nums_base, base_series, color="grey", linewidth=1.5,
                marker="o", markersize=3, label="Baseline (untrained)", alpha=0.8)
        ax.axhline(base_mean, color="grey", linestyle="--", linewidth=1.0,
                   alpha=0.6, label=f"Baseline mean ({base_mean:.2f})")

        if trained:
            train_series = _collect_final_rewards(trained, key)
            ax.plot(ep_nums_train, train_series, color="steelblue", linewidth=1.5,
                    marker="s", markersize=3, label="Trained", alpha=0.9)

        ax.set_title(label, fontsize=10)
        ax.set_xlabel("Episode", fontsize=8)
        ax.set_ylabel("Reward", fontsize=8)
        ax.set_ylim(0, 1)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=6, loc="lower right")

    plt.tight_layout()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    plt.savefig(str(output_path), dpi=150)
    pdf_path = output_path.with_suffix(".pdf")
    plt.savefig(str(pdf_path))
    plt.close()

    print(f"Saved PNG -> {output_path}")
    print(f"Saved PDF -> {pdf_path}")

    print("\nImprovement Summary:")
    for key in _REWARD_KEYS:
        base_vals = _collect_final_rewards(baseline, key)
        base_mean = float(np.mean(base_vals))
        if trained:
            train_vals = _collect_final_rewards(trained, key)
            train_mean = float(np.mean(train_vals))
            delta = train_mean - base_mean
            label = key.upper()
            print(f"  {label}: baseline={base_mean:.2f} → trained={train_mean:.2f} ({delta:+.2f})")
        else:
            print(f"  {key.upper()}: baseline={base_mean:.2f} → trained=N/A (no training log)")


if __name__ == "__main__":
    import sys
    kwargs = {}
    if "--baseline" in sys.argv:
        kwargs["baseline_log_path"] = sys.argv[sys.argv.index("--baseline") + 1]
    if "--trained" in sys.argv:
        kwargs["training_log_path"] = sys.argv[sys.argv.index("--trained") + 1]
    if "--output" in sys.argv:
        kwargs["output_path"] = sys.argv[sys.argv.index("--output") + 1]
    plot_training_curves(**kwargs)
