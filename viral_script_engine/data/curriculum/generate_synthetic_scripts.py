#!/usr/bin/env python3
"""
Generate synthetic scripts for curriculum tiers using the Anthropic API.
Run once to populate data/curriculum/synthetic_scripts.json.

Usage: python data/curriculum/generate_synthetic_scripts.py
"""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from viral_script_engine.agents.llm_backend import LLMBackend

OUTPUT_PATH = Path(__file__).parent / "synthetic_scripts.json"

FLAW_DIFFICULTY_MAP = {
    "easy":   ["buried_hook", "no_cta", "buried_hook", "no_cta", "buried_hook",
                "no_cta", "buried_hook", "no_cta", "buried_hook", "no_cta"],
    "medium": ["pacing_issue", "coherence_break", "cultural_mismatch", "pacing_issue", "coherence_break"],
    "hard":   ["conflicting_advice", "retention_risk", "cta_buried", "conflicting_advice", "retention_risk"],
}

NICHE_REGION_COMBOS = [
    ("personal finance", "Mumbai Gen Z", "Reels"),
    ("fashion", "Mumbai Gen Z", "Reels"),
    ("tech", "Pan-India English", "Shorts"),
    ("agriculture", "Tier-2 Hindi belt", "Reels"),
    ("small business", "Tier-2 Hindi belt", "Reels"),
    ("local culture", "Hinglish", "Reels"),
    ("startup advice", "Pan-India English", "Shorts"),
    ("productivity", "Pan-India English", "Reels"),
    ("fitness", "Mumbai Gen Z", "Reels"),
    ("cooking", "Tier-2 Hindi belt", "Reels"),
]

SYSTEM_PROMPT = (
    "You are a short-form video scriptwriter for Indian social media creators. "
    "Write realistic scripts that feel authentic — not like AI-generated content. "
    "Respond ONLY with the script text, no preamble or labels."
)

_FLAW_DESCRIPTIONS = {
    "buried_hook":       "the hook (opening line) appears only after 10–15 seconds of backstory",
    "no_cta":            "the script ends abruptly with no call-to-action or next step for viewers",
    "pacing_issue":      "the script rushes through key points and has an uneven tempo",
    "coherence_break":   "the script jumps between unrelated ideas mid-way, breaking narrative flow",
    "cultural_mismatch": "the script uses references or language that feel foreign to the target region",
    "conflicting_advice":"the script gives two pieces of advice that contradict each other",
    "retention_risk":    "the middle third of the script drops energy and is likely to cause drop-off",
    "cta_buried":        "there is a call-to-action but it is buried mid-script instead of at the end",
}


def _build_user_prompt(niche: str, region: str, platform: str, flaw: str, difficulty: str) -> str:
    flaw_desc = _FLAW_DESCRIPTIONS.get(flaw, flaw)
    return (
        f"Generate a realistic 60–90 second {platform} script for [{niche}] targeting [{region}].\n"
        f"Intentionally include [{flaw}] as the dominant flaw: {flaw_desc}.\n"
        f"The flaw should be [{difficulty}] to diagnose.\n"
        f"Write naturally — use the local language style for the region. Do not label the flaw."
    )


def generate_scripts() -> list:
    llm = LLMBackend(backend="anthropic", model_name="claude-haiku-4-5-20251001")
    results = []
    script_counter = {"easy": 0, "medium": 0, "hard": 0}

    for difficulty, flaws in FLAW_DIFFICULTY_MAP.items():
        for i, flaw in enumerate(flaws):
            combo = NICHE_REGION_COMBOS[i % len(NICHE_REGION_COMBOS)]
            niche, region, platform = combo
            script_counter[difficulty] += 1
            script_id = f"SYN_{difficulty[0].upper()}{script_counter[difficulty]:02d}"

            print(f"  Generating {script_id} ({difficulty}, {flaw}, {niche}/{region})...")
            user_prompt = _build_user_prompt(niche, region, platform, flaw, difficulty)
            try:
                script_text = llm.generate(SYSTEM_PROMPT, user_prompt, max_tokens=600)
            except Exception as e:
                print(f"    ERROR: {e} — using placeholder")
                script_text = f"[Synthetic {difficulty} script for {niche}/{region} with {flaw} — generation failed]"

            results.append({
                "script_id": script_id,
                "difficulty": difficulty,
                "region": region,
                "platform": platform,
                "niche": niche,
                "dominant_flaw": flaw,
                "script_text": script_text,
                "is_synthetic": True,
            })

    return results


def main():
    print("Generating synthetic scripts via Anthropic API...")
    print(f"Target: 10 easy + 5 medium + 5 hard = 20 total")

    scripts = generate_scripts()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(scripts, f, indent=2, ensure_ascii=False)

    counts = {}
    for s in scripts:
        counts[s["difficulty"]] = counts.get(s["difficulty"], 0) + 1
    print(f"\nSaved {len(scripts)} scripts -> {OUTPUT_PATH}")
    for diff, count in sorted(counts.items()):
        print(f"  {diff}: {count}")


if __name__ == "__main__":
    main()
