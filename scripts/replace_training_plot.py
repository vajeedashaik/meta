"""
Run this immediately after full GRPO training completes onsite.
Replaces the synthetic training plot with the real one.

Usage:
  python scripts/replace_training_plot.py --training-log logs/training_results.json
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from viral_script_engine.training.reward_curves import plot_training_curves

parser = argparse.ArgumentParser()
parser.add_argument("--training-log", required=True)
args = parser.parse_args()

plot_training_curves(
    baseline_log_path="logs/baseline_results.json",
    training_log_path=args.training_log,
    output_path="logs/training_vs_baseline.png",
    is_synthetic=False,
)
print("REAL training plot saved to logs/training_vs_baseline.png")
print("Commit this file to the repo immediately.")
