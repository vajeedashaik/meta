# Phase 11 — Longitudinal Episode Memory
> Paste this entire prompt into a fresh Claude Code session. Phase 10 must be complete before starting.

---

Phase 10 is complete. The A/B environment is running. Now add Longitudinal Episode Memory — transforming the system from a one-shot script coach into a persistent creative collaborator that remembers what it has learned about each creator across sessions.

**The current limitation:** Every episode is stateless. The Arbitrator knows nothing about what happened in previous episodes for this creator. If it successfully fixed the same creator's hook weakness three episodes in a row, it has no memory of that — it will re-diagnose the same issue from scratch every time.

**What this phase adds:** A Creator History Buffer that compresses the last 5 episodes for each creator into a structured memory. The Arbitrator observes this history at `reset()` and can make decisions informed by it — "this creator has a recurring hook problem and a strong cultural voice that must be preserved."

**Why this hits Theme 2 (long-horizon planning):** The participant guide defines Theme 2 as environments requiring the agent to track state over extended trajectories and recover from early mistakes. A cross-episode memory is the clearest possible implementation of long-horizon planning. This makes your submission touch Themes 1, 2, and 4 simultaneously.

**Meta deployment pitch:** This turns the system into a persistent coach. Meta could attach a Creator History Buffer to every creator account and the Arbitrator would accumulate personalised knowledge over time — no retraining, just growing memory.

---

## New files to create

```
viral_script_engine/
├── memory/
│   ├── __init__.py
│   ├── creator_history.py        # NEW — history buffer schema and management
│   ├── memory_compressor.py      # NEW — compresses episode logs into memory entries
│   └── history_store.py          # NEW — persistence layer for creator histories
├── data/
│   └── creator_histories/        # NEW — per-creator history files (JSON)
└── tests/
    └── test_phase11.py           # NEW
```

---

## Step 1 — `memory/creator_history.py`

```python
from pydantic import BaseModel
from typing import List, Optional, Dict

class EpisodeMemory(BaseModel):
    episode_id: str
    episode_number: int             # sequential count for this creator
    script_niche: str
    platform: str
    dominant_flaw: str              # the critique class that dominated this episode
    actions_taken: List[str]        # list of action_types executed in order
    what_worked: List[str]          # reward components that improved this episode
    what_didnt: List[str]           # reward components that dropped this episode
    final_total_reward: float
    key_learning: str               # one-sentence summary (rule-based, not LLM)

class CreatorHistoryBuffer(BaseModel):
    creator_id: str
    total_episodes: int
    recent_episodes: List[EpisodeMemory]    # last 5 episodes only (sliding window)
    recurring_weak_points: List[str]        # critique classes appearing in >=3 of last 5 episodes
    recurring_strong_points: List[str]      # reward components consistently >= 0.7
    most_effective_action: Optional[str]    # action_type with highest avg reward delta
    voice_stability_score: float            # how consistent R3 (cultural) has been (0–1)
    improvement_trend: str                  # "improving" | "plateauing" | "declining"

    def to_prompt_context(self) -> str:
        """
        Formats the history buffer as a concise string for the Arbitrator's prompt.
        Must be under 200 words — the Arbitrator's context window is limited.

        Format:
        CREATOR HISTORY (last {n} sessions):
        Recurring weak points: {recurring_weak_points}
        Recurring strengths: {recurring_strong_points}
        Most effective fix: {most_effective_action}
        Voice stability: {voice_stability_score:.0%}
        Trend: {improvement_trend}
        Last session: fixed {last_dominant_flaw} with {last_action}, reward {last_reward:.2f}
        """
```

---

## Step 2 — `memory/memory_compressor.py`

Converts a completed episode log into an `EpisodeMemory` entry. Rule-based — zero LLM calls.

```python
class MemoryCompressor:
    """
    Compresses a completed episode into a structured EpisodeMemory.
    Called at the end of every episode, before the next reset().
    Zero LLM calls — all compression is rule-based.
    """

    def compress(self, episode_log: dict, episode_number: int) -> EpisodeMemory:
        """
        episode_log is the JSON saved to logs/episode_<id>.json

        Algorithm:
        1. dominant_flaw: critique_class with most claims in step 1 Critic output
        2. actions_taken: list of action_types from each step's DebateRound
        3. what_worked: reward components with positive delta (final - initial > 0.05)
        4. what_didnt: reward components with negative delta (final - initial < -0.05)
        5. key_learning: rule-based template:
           "Fixed {dominant_flaw} using {most_used_action}. {what_worked[0]} improved, {what_didnt[0] or 'no regressions'}."
        """

    def update_buffer(
        self,
        existing_buffer: Optional[CreatorHistoryBuffer],
        new_memory: EpisodeMemory,
        creator_id: str,
    ) -> CreatorHistoryBuffer:
        """
        Adds new_memory to the buffer, maintaining a sliding window of 5.
        Recomputes:
        - recurring_weak_points: critique classes in >=3 of last 5 episodes
        - recurring_strong_points: reward components >= 0.7 in >=4 of last 5
        - most_effective_action: action with highest avg (final_reward - initial_reward)
        - voice_stability_score: std dev of r3_cultural_alignment across last 5 episodes, inverted
        - improvement_trend: slope of final_total_reward across last 5 episodes
          positive slope → "improving", near-zero → "plateauing", negative → "declining"
        """
```

---

## Step 3 — `memory/history_store.py`

```python
import json
import os

class HistoryStore:
    """
    Persists CreatorHistoryBuffers to disk, one file per creator.
    Simple key-value store — no database needed.
    """

    def __init__(self, store_dir: str = "data/creator_histories"):
        os.makedirs(store_dir, exist_ok=True)
        self.store_dir = store_dir

    def load(self, creator_id: str) -> Optional[CreatorHistoryBuffer]:
        path = os.path.join(self.store_dir, f"{creator_id}.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return CreatorHistoryBuffer(**json.load(f))

    def save(self, buffer: CreatorHistoryBuffer):
        path = os.path.join(self.store_dir, f"{buffer.creator_id}.json")
        with open(path, "w") as f:
            json.dump(buffer.dict(), f, indent=2)

    def list_creators(self) -> List[str]:
        return [f.replace(".json", "") for f in os.listdir(self.store_dir) if f.endswith(".json")]
```

---

## Step 4 — Update `environment/observations.py`

Add history buffer to `Observation`:

```python
class Observation(BaseModel):
    # ... existing fields ...
    creator_history: Optional[CreatorHistoryBuffer] = None   # NEW — None for first-time creators
    history_context: Optional[str] = None                    # NEW — formatted prompt string
```

---

## Step 5 — Update `environment/env.py`

In `__init__()`:
```python
self.memory_compressor = MemoryCompressor()
self.history_store = HistoryStore()
```

In `reset()`:
```python
# Load existing history for this creator (None if first episode)
creator_id = self._current_script_config.get("creator_id", "default")
history_buffer = self.history_store.load(creator_id)

# Add to observation
obs.creator_history = history_buffer
obs.creator_history_context = history_buffer.to_prompt_context() if history_buffer else None
```

In `step()`, after episode terminates (terminated=True):
```python
# Compress episode into memory and save
new_memory = self.memory_compressor.compress(
    episode_log=self._build_episode_log(),
    episode_number=(history_buffer.total_episodes + 1) if history_buffer else 1,
)
updated_buffer = self.memory_compressor.update_buffer(history_buffer, new_memory, creator_id)
self.history_store.save(updated_buffer)
```

---

## Step 6 — Update `training/rollout_function.py`

Add history context to the Arbitrator's prompt:

```
<|user|>
...existing fields...

CREATOR HISTORY:
{history_context or "First session — no history available"}

Choose your action:
<|end|>
```

---

## Step 7 — `scripts/run_longitudinal_demo.py`

Simulates a creator returning for 6 consecutive sessions, showing how the history buffer accumulates and how the Arbitrator's decisions change as it learns more about the creator.

```
python scripts/run_longitudinal_demo.py --creator S01 --sessions 6 --verbose
```

Output:
```
SESSION 1 (no history)
  Dominant flaw: hook_weakness
  Action taken: hook_rewrite
  Final reward: 0.58
  Memory saved: "First session. Fixed hook_weakness. R1 improved."

SESSION 2 (1 session history)
  History context: "Recurring weak: hook_weakness. Last session: hook improved."
  Dominant flaw: cultural_mismatch
  Action taken: cultural_ref_sub  ← different decision than session 1
  Final reward: 0.67

SESSION 3–6: [continue pattern...]

PROGRESSION SUMMARY:
  Rewards: 0.58 → 0.67 → 0.71 → 0.74 → 0.76 → 0.79
  Trend: improving
  Recurring weak point resolved by session 4: hook_weakness
  Voice stability: 0.91 (creator's cultural voice consistently preserved)
```

---

## Step 8 — Update `demo/run_demo.py`

If a history file exists for the script's creator, show it in Act 1:

```
╔══ CREATOR HISTORY ══════════════════════════════════════╗
│ Sessions: 3  |  Trend: improving  |  Voice: 89% stable  │
│ Recurring weak: hook_weakness (3/3 sessions)             │
│ Most effective fix: hook_rewrite (+0.22 avg)             │
│ Last session: R1 improved, no R3 regressions             │
╚══════════════════════════════════════════════════════════╝
```

---

## Step 9 — `tests/test_phase11.py`

- `MemoryCompressor.compress()` correctly extracts dominant_flaw, actions_taken, what_worked/didnt
- `MemoryCompressor.update_buffer()` maintains 5-episode sliding window correctly (drops oldest on episode 6)
- `recurring_weak_points` correctly identifies classes in >=3 of last 5 episodes
- `voice_stability_score` is high (>=0.8) for consistent R3, low (<0.5) for volatile R3
- `improvement_trend` correctly classifies improving/plateauing/declining from 5 reward values
- `HistoryStore` saves and loads correctly; `load()` returns None for unknown creator
- `env.reset()` loads history for returning creator, None for new creator
- `env.step()` saves updated history after episode termination
- `to_prompt_context()` output is under 200 words

---

## Gate check

Run:
```
python scripts/run_longitudinal_demo.py --creator S01 --sessions 6 --verbose
```

Must:
1. Complete 6 sessions without error
2. Show history buffer growing across sessions
3. Show the Arbitrator's decisions changing in later sessions (evidence it's using history)
4. Save 6 history files to `data/creator_histories/`
5. Print:
   ```
   PHASE 11 GATE: PASS — Longitudinal memory active. 6 sessions completed. Final reward trend: {trend}.
   ```