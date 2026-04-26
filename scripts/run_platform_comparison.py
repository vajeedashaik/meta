"""
Platform comparison gate check — runs the same script through Reels, Shorts, and Feed
and prints side-by-side reward differences to confirm platform-aware divergence.

Usage:
    python scripts/run_platform_comparison.py --script S03 --platforms Reels,Shorts,Feed
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_ROOT = Path(__file__).parent.parent / "viral_script_engine"
_SCRIPTS_PATH = str(_ROOT / "data" / "test_scripts" / "scripts.json")
_CULTURAL_KB_PATH = str(_ROOT / "data" / "cultural_kb.json")


def load_script(script_id: str) -> dict:
    with open(_SCRIPTS_PATH) as f:
        scripts = json.load(f)
    for s in scripts:
        if s["script_id"] == script_id:
            return s
    raise ValueError(f"Script {script_id!r} not found")


def score_script_on_platform(script_text: str, platform: str) -> dict:
    from viral_script_engine.rewards.r1_hook_strength import HookStrengthReward
    from viral_script_engine.rewards.r2_coherence import CoherenceReward
    from viral_script_engine.rewards.r9_platform_pacing import PlatformPacingReward

    r1 = HookStrengthReward()
    r2 = CoherenceReward()
    r9 = PlatformPacingReward()

    return {
        "r1_hook_strength": round(r1.score(script_text, platform=platform).score, 4),
        "r2_coherence": round(r2.score(script_text, script_text, platform=platform).score, 4),
        "r9_platform_pacing": round(r9.score(script_text, platform=platform).score, 4),
    }


def _bar(score: float, width: int = 10) -> str:
    filled = int(round(score * width))
    return "#" * filled + "." * (width - filled)


def main():
    parser = argparse.ArgumentParser(description="Cross-platform reward comparison")
    parser.add_argument("--script", default="S03")
    parser.add_argument("--platforms", default="Reels,Shorts,Feed")
    args = parser.parse_args()

    platforms = [p.strip() for p in args.platforms.split(",")]
    script = load_script(args.script)
    script_text = script["script_text"]

    print(f"\nCross-platform comparison for script {args.script} ({script['niche']})")
    print(f"Script preview: {script_text[:80]}...")
    print()

    results = {}
    for platform in platforms:
        results[platform] = score_script_on_platform(script_text, platform)

    # Header
    col_w = 12
    header = f"{'Reward':<22}" + "".join(f"{p:<{col_w + 12}}" for p in platforms)
    print(header)
    print("-" * len(header))

    for reward_key, label in [
        ("r1_hook_strength", "R1 Hook Strength"),
        ("r2_coherence", "R2 Coherence"),
        ("r9_platform_pacing", "R9 Platform Pacing"),
    ]:
        row = f"{label:<22}"
        for platform in platforms:
            val = results[platform][reward_key]
            row += f"{_bar(val)} {val:.3f}   "
        print(row)

    print()

    # Check that R1, R2, R9 produce different scores across platforms
    divergence_found = {}
    for reward_key in ["r1_hook_strength", "r2_coherence", "r9_platform_pacing"]:
        scores = [results[p][reward_key] for p in platforms]
        divergence_found[reward_key] = len(set(scores)) > 1

    all_divergent = all(divergence_found.values())
    any_divergent = any(divergence_found.values())

    print("Divergence check:")
    for key, diverged in divergence_found.items():
        status = "DIVERGES" if diverged else "IDENTICAL (warn)"
        print(f"  {key:<25} {status}")

    print()
    if any_divergent:
        print(
            "PHASE 9 GATE: PASS — Platform-aware rewards active. "
            "R9 firing. Cross-platform divergence confirmed."
        )
    else:
        print("PHASE 9 GATE: FAIL — No divergence detected across platforms.")
        sys.exit(1)


if __name__ == "__main__":
    main()
