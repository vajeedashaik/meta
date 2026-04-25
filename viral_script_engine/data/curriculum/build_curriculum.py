#!/usr/bin/env python3
"""
Build curriculum tiers from existing test scripts + synthetic scripts.
Generates:
  - easy_tier.jsonl   (20 configs)
  - medium_tier.jsonl (15 configs)
  - hard_tier.jsonl   (10 configs)

Usage: python data/curriculum/build_curriculum.py
  (Run generate_synthetic_scripts.py first if synthetic_scripts.json is missing)
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
CURRICULUM_DIR = DATA_DIR / "curriculum"
SCRIPTS_PATH = DATA_DIR / "test_scripts" / "scripts.json"
SYNTHETIC_PATH = CURRICULUM_DIR / "synthetic_scripts.json"

sys.path.insert(0, str(BASE_DIR.parent))

_FLAW_TO_CRITIQUE_CLASS = {
    "buried_hook":       "hook_weakness",
    "no_cta":            "cta_weakness",
    "pacing_issue":      "coherence_issue",
    "coherence_break":   "coherence_issue",
    "cultural_mismatch": "cultural_misalignment",
    "conflicting_advice":"coherence_issue",
    "retention_risk":    "hook_weakness",
    "cta_buried":        "cta_weakness",
}

_FLAW_TO_ACTION = {
    "buried_hook":       "hook_rewrite",
    "no_cta":            "cta_placement",
    "pacing_issue":      "section_reorder",
    "coherence_break":   "section_reorder",
    "cultural_mismatch": "cultural_ref_sub",
    "conflicting_advice":"section_reorder",
    "retention_risk":    "hook_rewrite",
    "cta_buried":        "cta_placement",
}

_EASY_NOTES = "One obvious flaw. Critic should win immediately. Strong reward signal on step 1."
_MEDIUM_NOTES = "Trade-off scenario. Critic and Defender both have valid points. Reward signal emerges over 2–3 steps."
_HARD_NOTES = "Fixing the top critique risks damaging R3 cultural alignment. Explicit reward conflict."


def _load_json(path: Path) -> list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _make_config(
    config_id: str,
    difficulty: str,
    script: dict,
    notes: str,
) -> dict:
    flaws = script.get("known_flaws", script.get("dominant_flaw", ["buried_hook"]))
    if isinstance(flaws, str):
        flaws = [flaws]
    dominant = flaws[0] if flaws else "buried_hook"
    return {
        "episode_config_id": config_id,
        "difficulty": difficulty,
        "script_id": script["script_id"],
        "script_text": script["script_text"],
        "region": script["region"],
        "platform": script["platform"],
        "niche": script["niche"],
        "dominant_flaw": dominant,
        "expected_critique_class": _FLAW_TO_CRITIQUE_CLASS.get(dominant, "hook_weakness"),
        "expected_action": _FLAW_TO_ACTION.get(dominant, "hook_rewrite"),
        "curriculum_notes": notes,
    }


def build_easy_tier(existing: list, synthetic: list) -> list:
    """
    20 configs: 10 from existing easy scripts (S01–S04) + 10 from synthetic easy.
    Existing scripts are used with slight context variations (platform/region cycling).
    """
    easy_existing = [s for s in existing if s["script_id"] in ("S01", "S02", "S03", "S04")]
    easy_synthetic = [s for s in synthetic if s["difficulty"] == "easy"]

    configs = []
    idx = 1

    region_variants = ["Mumbai Gen Z", "Pan-India English", "Tier-2 Hindi belt"]
    platform_variants = ["Reels", "Shorts", "Reels"]

    for i, script in enumerate(easy_existing * 3):
        if len(configs) >= 10:
            break
        variant = i % len(region_variants)
        patched = dict(script)
        patched["region"] = region_variants[variant]
        patched["platform"] = platform_variants[variant]
        cfg = _make_config(f"easy_{idx:03d}", "easy", patched, _EASY_NOTES)
        configs.append(cfg)
        idx += 1

    for script in easy_synthetic[:10]:
        cfg = _make_config(f"easy_{idx:03d}", "easy", script, _EASY_NOTES)
        configs.append(cfg)
        idx += 1

    return configs[:20]


def build_medium_tier(existing: list, synthetic: list) -> list:
    """
    15 configs: 10 from medium scripts (S05–S07) + 5 from synthetic medium.
    """
    med_existing = [s for s in existing if s["script_id"] in ("S05", "S06", "S07")]
    med_synthetic = [s for s in synthetic if s["difficulty"] == "medium"]

    configs = []
    idx = 1

    for i, script in enumerate(med_existing * 5):
        if len(configs) >= 10:
            break
        cfg = _make_config(f"medium_{idx:03d}", "medium", script, _MEDIUM_NOTES)
        configs.append(cfg)
        idx += 1

    for script in med_synthetic[:5]:
        cfg = _make_config(f"medium_{idx:03d}", "medium", script, _MEDIUM_NOTES)
        configs.append(cfg)
        idx += 1

    return configs[:15]


def build_hard_tier(existing: list, synthetic: list) -> list:
    """
    10 configs: 5 from hard scripts (S08–S10) + 5 from synthetic hard.
    """
    hard_existing = [s for s in existing if s["script_id"] in ("S08", "S09", "S10")]
    hard_synthetic = [s for s in synthetic if s["difficulty"] == "hard"]

    configs = []
    idx = 1

    for i, script in enumerate(hard_existing * 4):
        if len(configs) >= 5:
            break
        cfg = _make_config(f"hard_{idx:03d}", "hard", script, _HARD_NOTES)
        configs.append(cfg)
        idx += 1

    for script in hard_synthetic[:5]:
        cfg = _make_config(f"hard_{idx:03d}", "hard", script, _HARD_NOTES)
        configs.append(cfg)
        idx += 1

    return configs[:10]


def write_jsonl(configs: list, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for cfg in configs:
            f.write(json.dumps(cfg, ensure_ascii=False) + "\n")
    print(f"  Wrote {len(configs)} configs -> {path.name}")


def main():
    existing = _load_json(SCRIPTS_PATH)
    print(f"Loaded {len(existing)} existing scripts.")

    if SYNTHETIC_PATH.exists():
        synthetic = _load_json(SYNTHETIC_PATH)
        print(f"Loaded {len(synthetic)} synthetic scripts.")
    else:
        print(f"WARNING: {SYNTHETIC_PATH} not found — using empty list.")
        print("Run generate_synthetic_scripts.py first for full curriculum.")
        synthetic = []

    easy = build_easy_tier(existing, synthetic)
    medium = build_medium_tier(existing, synthetic)
    hard = build_hard_tier(existing, synthetic)

    write_jsonl(easy,   CURRICULUM_DIR / "easy_tier.jsonl")
    write_jsonl(medium, CURRICULUM_DIR / "medium_tier.jsonl")
    write_jsonl(hard,   CURRICULUM_DIR / "hard_tier.jsonl")

    print(f"\nCurriculum built: easy={len(easy)}, medium={len(medium)}, hard={len(hard)}")


if __name__ == "__main__":
    main()
