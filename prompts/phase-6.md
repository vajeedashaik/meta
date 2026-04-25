# Phase 6 — Moderation Agent + Originality Agent
> Paste this entire prompt into a fresh Claude Code session. Phase 5 must be complete and the HF Space live before starting.

---

Phase 5 is complete. The environment is deployed and the demo runs. Now add two new agents — Moderation and Originality — that plug into the existing `step()` loop as additional observers. The Arbitrator's job gets harder: it now has to weigh five expert opinions instead of three before making one decision.

**What stays the same:** The RL structure is completely unchanged. `reset()`, `step(action)`, `state()`, `reward()` all have the same signatures. The Arbitrator still takes exactly one action per step.

**What changes:** Two new agents run inside `step()` alongside the Critic and Defender. Two new reward signals (R6, R7) are added to `RewardComponents`. The `RewardAggregator` is updated to incorporate them with new weights.

---

## New files to create

```
viral_script_engine/
├── agents/
│   ├── moderation_agent.py       # NEW
│   └── originality_agent.py      # NEW
├── rewards/
│   ├── r6_safety.py              # NEW
│   └── r7_originality.py         # NEW
├── data/
│   ├── shadowban_triggers.json   # NEW — rule-based moderation kb
│   └── viral_templates.json      # NEW — overused format corpus
└── tests/
    └── test_phase6.py            # NEW
```

---

## Step 1 — `data/shadowban_triggers.json`

Create a JSON knowledge base of content patterns that get flagged or shadowbanned on Reels. Organise into categories:

```json
{
  "hate_speech_patterns": [
    "list of phrases, slurs, dog whistles — keep clinical, for detection purposes only"
  ],
  "misleading_health_claims": [
    "cure", "doctors don't want you to know", "guaranteed weight loss",
    "100% natural treatment", "miracle remedy", "big pharma hiding"
  ],
  "copyright_bait_phrases": [
    "full movie", "free download", "watch without ads", "leaked footage"
  ],
  "engagement_bait": [
    "comment if you agree", "share to save", "follow or bad luck",
    "tag 3 friends", "double tap if"
  ],
  "spam_signals": [
    "link in bio for free", "dm me the word", "click the link below for"
  ],
  "platform_policy_violations": [
    "buy followers", "get rich quick", "make $X in Y days guaranteed"
  ]
}
```

Include at least 15 entries per category. All entries are lowercase for case-insensitive matching.

---

## Step 2 — `agents/moderation_agent.py`

Fully rule-based — zero LLM calls. Fast lookup against `shadowban_triggers.json`.

```python
from pydantic import BaseModel
from typing import List, Dict

class ModerationFlag(BaseModel):
    category: str           # which category triggered: "hate_speech" | "misleading_health" | "copyright_bait" | "engagement_bait" | "spam" | "policy_violation"
    trigger_phrase: str     # exact phrase that matched
    position: str           # "hook" | "body" | "cta" — which section of the script
    severity: str           # "low" | "medium" | "high"
    suggestion: str         # one-line fix suggestion

class ModerationOutput(BaseModel):
    flags: List[ModerationFlag]
    is_safe: bool           # True if zero high-severity flags
    overall_risk: str       # "safe" | "low_risk" | "medium_risk" | "high_risk"
    total_flags: int

class ModerationAgent:
    """
    Checks scripts for content that would get flagged or shadowbanned on Reels.
    Zero LLM calls — purely rule-based against shadowban_triggers.json.
    Fast enough to run on every step() call without slowing the episode loop.
    """

    SEVERITY_MAP = {
        "hate_speech_patterns": "high",
        "misleading_health_claims": "high",
        "copyright_bait_phrases": "medium",
        "engagement_bait": "low",
        "spam_signals": "medium",
        "platform_policy_violations": "high",
    }

    def __init__(self, kb_path: str = "data/shadowban_triggers.json"):
        # Load knowledge base once at init — do not reload per call
        pass

    def check(self, script: str) -> ModerationOutput:
        """
        1. Split script into hook (first 3 sentences), body, cta (last 2 sentences)
        2. For each section, scan against all trigger categories (case-insensitive)
        3. Record every match as a ModerationFlag
        4. is_safe = True only if zero "high" severity flags
        5. overall_risk based on total flags and highest severity present
        """
```

---

## Step 3 — `rewards/r6_safety.py`

```python
class SafetyReward:
    """
    Converts ModerationOutput into a reward signal.

    Scoring:
    - Zero flags:                    1.0
    - Only low-severity flags:       0.8
    - Any medium-severity flag:      0.5
    - Any high-severity flag:        0.0  (hard zero — no partial credit)

    The hard zero on high-severity is intentional: the Arbitrator must learn
    that some rewrites are categorically unacceptable regardless of other improvements.
    This is non-negotiable from Meta's platform policy perspective.
    """

    def score(self, moderation_output: ModerationOutput) -> SafetyRewardResult:
        # Returns SafetyRewardResult with: score, flag_count, highest_severity, breakdown
```

---

## Step 4 — `data/viral_templates.json`

A corpus of overused Reels/Shorts script patterns. These are formats so common they signal low originality to both the algorithm and viewers.

```json
{
  "overused_hooks": [
    "POV: you finally figured out",
    "nobody talks about this but",
    "things that are actually red flags",
    "tell me you're X without telling me you're X",
    "as someone who has done X for Y years",
    "the reason you're not seeing results is",
    "stop doing X immediately",
    "X things I wish I knew before"
  ],
  "overused_structures": [
    "hook → 3 numbered tips → CTA to follow",
    "controversial take → explanation → agree with me?",
    "before and after → what changed → product mention"
  ],
  "overused_cta_phrases": [
    "follow for more", "save this for later", "share with someone who needs this",
    "comment your thoughts below", "like if you agree"
  ],
  "overused_transitions": [
    "but wait there's more", "and here's the thing", "plot twist",
    "but actually", "real talk though"
  ]
}
```

Include at least 20 entries per category.

---

## Step 5 — `agents/originality_agent.py`

Fully rule-based — zero LLM calls. Checks how much the script overlaps with known viral templates.

```python
class OriginalityFlag(BaseModel):
    template_type: str      # "overused_hook" | "overused_structure" | "overused_cta" | "overused_transition"
    matched_pattern: str    # which template was matched
    script_excerpt: str     # the part of the script that matched
    suggestion: str         # one-line suggestion to make it more original

class OriginalityOutput(BaseModel):
    flags: List[OriginalityFlag]
    originality_score: float    # 0–1, computed before reward mapping
    is_generic: bool            # True if originality_score < 0.4
    unique_elements: List[str]  # parts of the script that DON'T match any template (positive signal)

class OriginalityAgent:
    """
    Measures how distinct the script sounds compared to overused Reels formats.
    Zero LLM calls — fuzzy string matching against viral_templates.json.

    Uses difflib.SequenceMatcher for fuzzy matching (threshold: 0.75 similarity).
    Exact substring match alone misses paraphrased templates.
    """

    def __init__(self, templates_path: str = "data/viral_templates.json"):
        pass

    def check(self, script: str) -> OriginalityOutput:
        """
        1. Extract hook, body, CTA sections
        2. For each section, fuzzy-match against all template categories
        3. originality_score = 1 - (matched_sections / total_sections)
        4. unique_elements = sentences with zero template matches (positive signal for judges)
        """
```

---

## Step 6 — `rewards/r7_originality.py`

```python
class OriginalityReward:
    """
    Converts OriginalityOutput into a reward signal.

    Scoring maps directly from originality_score:
    - originality_score >= 0.8:  reward = 1.0  (genuinely distinctive)
    - originality_score 0.6–0.8: reward = originality_score
    - originality_score 0.4–0.6: reward = 0.3  (mediocre — generic but not terrible)
    - originality_score < 0.4:   reward = 0.0  (this is a template clone)

    The cliff at 0.4 is intentional: the Arbitrator must learn that
    generic rewrites are penalised even if other signals improve.
    """

    def score(self, originality_output: OriginalityOutput) -> OriginalityRewardResult:
        pass
```

---

## Step 7 — Update `environment/observations.py`

Add fields to `RewardComponents`:
```python
r6_safety: Optional[float] = None
r7_originality: Optional[float] = None
```

Add fields to `DebateRound`:
```python
moderation_output: Optional[ModerationOutput] = None
originality_output: Optional[OriginalityOutput] = None
```

Add fields to `Observation` — the Arbitrator now sees moderation and originality signals before deciding:
```python
current_moderation_flags: List[ModerationFlag] = []
current_originality_flags: List[OriginalityFlag] = []
```

---

## Step 8 — Update `environment/env.py`

In `__init__()`, add:
```python
self.moderation_agent = ModerationAgent()
self.originality_agent = OriginalityAgent()
self.r6 = SafetyReward()
self.r7 = OriginalityReward()
```

In `step()`, after the Rewriter executes and before RewardAggregator runs:
```python
# Run new agents on the rewritten script
moderation_out = self.moderation_agent.check(new_script)
originality_out = self.originality_agent.check(new_script)

# Compute new rewards
components.r6_safety = self.r6.score(moderation_out).score
components.r7_originality = self.r7.score(originality_out).score

# Store outputs in DebateRound for logging and demo
debate_round.moderation_output = moderation_out
debate_round.originality_output = originality_out
```

In `reset()`, also run both agents on the unmodified script to establish baseline R6/R7.

---

## Step 9 — Update `rewards/reward_aggregator.py`

Update weights to accommodate R6 and R7. Total must still sum to 1.0:

```python
WEIGHTS = {
    "r1": 0.20,   # hook strength
    "r2": 0.15,   # coherence
    "r3": 0.15,   # cultural alignment
    "r4": 0.15,   # debate resolution
    "r5": 0.15,   # defender preservation
    "r6": 0.10,   # safety
    "r7": 0.10,   # originality
}
```

The catastrophic drop penalty must now also watch R6 and R7. A rewrite that introduces a shadowban trigger (R6 drops to 0.0) must zero the entire step reward regardless of other scores.

---

## Step 10 — Update `demo/run_demo.py`

In Act 5 (The Rewrite + Reward), add R6 and R7 to the reward progress-bar display:

```
R1 Hook Strength    ██████░░  0.75
R2 Coherence        ████░░░░  0.60
R3 Cultural         ███████░  0.85
R4 Resolution       █████░░░  0.70
R5 Preservation     ██████░░  0.75
R6 Safety           ████████  1.00  ✓ No flags
R7 Originality      █████░░░  0.68  ⚠ 1 template match
─────────────────────────────────────
Total               ██████░░  0.76  (+38% vs baseline)
```

If any moderation flags were found, display them in a red panel between Act 3 and Act 4:
```
⛔ MODERATION FLAGS DETECTED
  [medium] engagement_bait in CTA: "comment if you agree" → suggest removing
```

---

## Step 11 — `tests/test_phase6.py`

- `ModerationAgent.check()` correctly flags high-severity content (test with 3 hand-crafted scripts containing known triggers)
- `ModerationAgent.check()` returns `is_safe=True` on a clean script
- `SafetyReward` returns 0.0 on any high-severity flag (hard zero)
- `OriginalityAgent.check()` correctly identifies overused hooks via fuzzy matching
- `OriginalityAgent.check()` returns `originality_score >= 0.8` on a genuinely unique script
- `OriginalityReward` returns 0.0 on a template clone
- `RewardAggregator` correctly incorporates R6/R7 with updated weights
- Catastrophic drop fires when R6 drops from 1.0 to 0.0 (shadowban trigger introduced by rewrite)
- `env.step()` includes moderation and originality outputs in `info` dict

---

## Gate check

Run:
```
python scripts/run_dummy_episode.py --difficulty easy --steps 3 --verbose
```

Must:
1. Complete without error with R6 and R7 now appearing in reward output
2. Show moderation and originality outputs in each DebateRound
3. Print:
   ```
   PHASE 6 GATE: PASS — R6 (safety) and R7 (originality) active. Total reward components: 7.
   ```