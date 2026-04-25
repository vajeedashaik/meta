# Phase 9 — Multi-Platform Reward Divergence
> Paste this entire prompt into a fresh Claude Code session. Phase 8 must be complete before starting.

---

Phase 8 is complete. Creator personas are active. Now make platform structurally affect the reward functions — not just as a label in the observation but as a real constraint that changes what "good" means for each reward.

**The current problem:** "platform" is just a string the Arbitrator reads. The reward functions treat Reels, Shorts, and Feed identically. In reality, these platforms have different retention curves, optimal hook lengths, CTA timing, and pacing norms. A hook that works on Reels (3-second drop-off window) fails on Feed (5-second window). The current environment cannot teach the Arbitrator this distinction.

**What this phase adds:** Platform-specific reward thresholds and scoring rubrics baked into R1, R2, R4, and a new R9 (platform pacing). The Arbitrator learns that the same script needs different fixes depending on where it is being posted.

**Meta deployment pitch:** Meta is competing with TikTok and YouTube Shorts simultaneously across different surfaces. A system that understands platform-specific optimisation is directly deployable across all their content surfaces without retraining.

---

## New files to create

```
viral_script_engine/
├── platforms/
│   ├── __init__.py
│   ├── platform_spec.py          # NEW — platform specs and thresholds
│   └── platform_kb.json          # NEW — platform rules knowledge base
├── rewards/
│   └── r9_platform_pacing.py     # NEW
└── tests/
    └── test_phase9.py            # NEW
```

---

## Step 1 — `platforms/platform_kb.json`

Define the platform-specific rules that reward functions will use:

```json
{
  "Reels": {
    "hook_window_seconds": 3,
    "optimal_script_length_words": 120,
    "max_script_length_words": 180,
    "hook_length_words": 15,
    "cta_position": "last_10_percent",
    "optimal_sentences_per_section": {"hook": 2, "body": 6, "cta": 1},
    "pacing_norm": "fast",
    "avg_retention_curve": "steep_drop_at_3s_then_gradual",
    "penalty_for_slow_start": true,
    "reward_for_pattern_interrupt": true,
    "notes": "Fastest drop-off. Hook must deliver value in 3 seconds. No warmup allowed."
  },
  "Shorts": {
    "hook_window_seconds": 2,
    "optimal_script_length_words": 80,
    "max_script_length_words": 120,
    "hook_length_words": 10,
    "cta_position": "last_5_percent",
    "optimal_sentences_per_section": {"hook": 1, "body": 4, "cta": 1},
    "pacing_norm": "very_fast",
    "avg_retention_curve": "steep_drop_at_2s",
    "penalty_for_slow_start": true,
    "reward_for_pattern_interrupt": true,
    "notes": "Shortest attention window. One-sentence hook maximum. Body must be dense."
  },
  "Feed": {
    "hook_window_seconds": 5,
    "optimal_script_length_words": 200,
    "max_script_length_words": 300,
    "hook_length_words": 25,
    "cta_position": "last_15_percent",
    "optimal_sentences_per_section": {"hook": 3, "body": 10, "cta": 2},
    "pacing_norm": "moderate",
    "avg_retention_curve": "gradual_decline",
    "penalty_for_slow_start": false,
    "reward_for_pattern_interrupt": false,
    "notes": "Longer attention window. Can build up to the hook. More space for nuance."
  },
  "TikTok": {
    "hook_window_seconds": 2,
    "optimal_script_length_words": 100,
    "max_script_length_words": 150,
    "hook_length_words": 12,
    "cta_position": "last_8_percent",
    "optimal_sentences_per_section": {"hook": 1, "body": 5, "cta": 1},
    "pacing_norm": "very_fast",
    "avg_retention_curve": "steep_drop_at_2s_recovery_possible",
    "penalty_for_slow_start": true,
    "reward_for_pattern_interrupt": true,
    "notes": "Similar to Shorts but with stronger recovery potential mid-video."
  }
}
```

---

## Step 2 — `platforms/platform_spec.py`

```python
from pydantic import BaseModel
from typing import Dict
import json

class PlatformSpec(BaseModel):
    platform: str
    hook_window_seconds: int
    optimal_script_length_words: int
    max_script_length_words: int
    hook_length_words: int
    cta_position: str
    optimal_sentences_per_section: Dict[str, int]
    pacing_norm: str
    penalty_for_slow_start: bool
    reward_for_pattern_interrupt: bool

class PlatformRegistry:
    """
    Loads and serves platform specs. Single source of truth for
    all platform-specific reward thresholds.
    """

    def __init__(self, kb_path: str = "platforms/platform_kb.json"):
        with open(kb_path) as f:
            raw = json.load(f)
        self.specs = {k: PlatformSpec(platform=k, **v) for k, v in raw.items()}

    def get(self, platform: str) -> PlatformSpec:
        if platform not in self.specs:
            raise ValueError(f"Unknown platform: {platform}. Valid: {list(self.specs.keys())}")
        return self.specs[platform]
```

---

## Step 3 — Update `rewards/r1_hook_strength.py`

Make hook scoring platform-aware. The current R1 uses a fixed 15-word threshold for front-loading. Replace with platform-specific thresholds:

```python
class HookStrengthReward:
    def __init__(self):
        self.platform_registry = PlatformRegistry()

    def score(self, script: str, platform: str = "Reels") -> HookRewardResult:
        spec = self.platform_registry.get(platform)

        # Check 1: PROMISE CHECK — unchanged
        # Check 2: CURIOSITY GAP — unchanged
        # Check 3: SPECIFICITY — unchanged

        # Check 4: FRONT-LOADING — now platform-aware
        # Use spec.hook_length_words instead of hardcoded 15
        # Hook must deliver its main signal within spec.hook_length_words words

        # Check 5: ANTI-FILLER — unchanged

        # NEW Check 6: LENGTH FIT — is the hook the right length for this platform?
        hook_word_count = len(hook_text.split())
        length_score = 1.0 if hook_word_count <= spec.hook_length_words else max(0, 1 - (hook_word_count - spec.hook_length_words) / spec.hook_length_words)

        # Score = (checks_1_to_5_passed / 5) * 0.85 + length_score * 0.15
```

Update `score()` signature: add `platform: str = "Reels"` parameter.

---

## Step 4 — Update `rewards/r2_coherence.py`

Add a platform length penalty. A rewrite that makes the script too long for the platform damages the coherence score even if semantic similarity is high:

```python
def score(self, original_script: str, current_script: str, platform: str = "Reels") -> CoherenceRewardResult:
    spec = self.platform_registry.get(platform)

    # Existing semantic similarity score (unchanged)
    semantic_score = self._compute_semantic_similarity(original_script, current_script)

    # NEW: length penalty
    word_count = len(current_script.split())
    if word_count > spec.max_script_length_words:
        length_penalty = (word_count - spec.max_script_length_words) / spec.max_script_length_words
        length_penalty = min(0.3, length_penalty)  # cap penalty at 0.3
    else:
        length_penalty = 0.0

    # Final score = mapped semantic_score - length_penalty, clipped to [0, 1]
```

---

## Step 5 — `rewards/r9_platform_pacing.py`

New reward signal that checks whether the script's pacing matches the platform norm.

```python
class PlatformPacingReward:
    """
    Measures whether the script's structure and pacing fit the target platform.
    Zero LLM calls — rule-based analysis of sentence structure and section lengths.

    Pacing is measured by:
    1. Sentence length distribution — short sentences = fast pacing
    2. Section length ratio — hook:body:cta ratio should match platform spec
    3. Information density in hook — high density = fast pacing
    4. CTA position — is the CTA in the right position for this platform?
    """

    def __init__(self):
        self.platform_registry = PlatformRegistry()

    def score(self, script: str, platform: str) -> PacingRewardResult:
        spec = self.platform_registry.get(platform)

        # Split into hook, body, cta sections (same logic as ModerationAgent)
        hook, body, cta = self._split_sections(script)

        # Check 1: Avg words per sentence in hook (lower = faster pacing)
        hook_avg_words = self._avg_words_per_sentence(hook)
        pacing_norm_threshold = {"very_fast": 8, "fast": 12, "moderate": 18}
        pacing_score = 1.0 if hook_avg_words <= pacing_norm_threshold[spec.pacing_norm] else max(0, 1 - (hook_avg_words - pacing_norm_threshold[spec.pacing_norm]) / pacing_norm_threshold[spec.pacing_norm])

        # Check 2: Section length ratio
        hook_words = len(hook.split())
        body_words = len(body.split())
        cta_words = len(cta.split())
        total_words = max(hook_words + body_words + cta_words, 1)

        optimal_hook_ratio = spec.optimal_sentences_per_section["hook"] / sum(spec.optimal_sentences_per_section.values())
        actual_hook_ratio = hook_words / total_words
        ratio_score = 1 - min(1, abs(actual_hook_ratio - optimal_hook_ratio) / optimal_hook_ratio)

        # Check 3: CTA position
        cta_start_position = (hook_words + body_words) / total_words
        cta_target = {"last_5_percent": 0.95, "last_8_percent": 0.92, "last_10_percent": 0.90, "last_15_percent": 0.85}
        cta_score = 1.0 if cta_start_position >= cta_target.get(spec.cta_position, 0.90) else 0.5

        # Final: weighted average of three checks
        final_score = pacing_score * 0.4 + ratio_score * 0.4 + cta_score * 0.2
        return PacingRewardResult(score=final_score, pacing_score=pacing_score, ratio_score=ratio_score, cta_score=cta_score, platform=platform)
```

---

## Step 6 — Update `environment/env.py`

In `__init__()`:
```python
self.r9 = PlatformPacingReward()
self.platform_registry = PlatformRegistry()
```

In `step()`, pass platform to all reward functions that now accept it:
```python
components.r1_hook_strength = self.r1.score(new_script, platform=self._current_platform).score
components.r2_coherence = self.r2.score(original, new_script, platform=self._current_platform).score
components.r9_platform_pacing = self.r9.score(new_script, platform=self._current_platform).score
```

Store `_current_platform` from the episode's script config at `reset()`.

Update `RewardComponents`:
```python
r9_platform_pacing: Optional[float] = None
```

Update `RewardAggregator` weights (9 rewards + process now):
```python
WEIGHTS = {
    "r1": 0.15, "r2": 0.12, "r3": 0.10,
    "r4": 0.10, "r5": 0.10, "r6": 0.08,
    "r7": 0.08, "r8": 0.08, "r9": 0.09,
    "process": 0.10,
}
```

---

## Step 7 — Update `data/curriculum/` JSONL files

Add platform diversity to the curriculum. Currently most configs default to "Reels". Update:
- easy_tier.jsonl: 50% Reels, 30% Shorts, 20% Feed
- medium_tier.jsonl: 40% Reels, 30% Shorts, 30% Feed
- hard_tier.jsonl: add cross-platform configs — same script, two different platforms, showing that the right fix differs by platform

---

## Step 8 — Update `demo/run_demo.py`

In Act 1 (The Raw Script), add platform spec to the display:
```
Platform: Reels  |  Hook window: 3s  |  Max length: 180 words  |  Pacing: fast
```

In Act 5 (The Rewrite + Reward), add R9 to the reward table:
```
R9 Platform Pacing  ███████░  0.82  ✓ Hook fits 3s window
```

---

## Step 9 — `tests/test_phase9.py`

- `PlatformRegistry.get()` returns correct spec for each platform
- `PlatformRegistry.get()` raises `ValueError` for unknown platform
- R1 scores lower for a hook that's too long for Shorts vs Reels
- R2 applies length penalty correctly when script exceeds `max_script_length_words`
- `PlatformPacingReward` scores higher for a fast-paced hook on Reels than a slow one
- `PlatformPacingReward` scores correctly for CTA position on each platform
- Same script scores differently on Reels vs Feed (this is the key proof the system works)
- `env.step()` passes platform correctly to all reward functions

---

## Gate check

Run:
```
python scripts/run_dummy_episode.py --difficulty easy --steps 3 --verbose
```

Then also run a cross-platform comparison test:
```
python scripts/run_platform_comparison.py --script S03 --platforms Reels,Shorts,Feed
```

Create `scripts/run_platform_comparison.py` — runs the same script through 3 episodes with different platforms and prints the reward differences side by side.

Must show that R1, R2, and R9 produce different scores for the same script across platforms. Print:
```
PHASE 9 GATE: PASS — Platform-aware rewards active. R9 firing. Cross-platform divergence confirmed.
```