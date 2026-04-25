# Phase 1 — OpenEnv Scaffold + R1/R2 Rewards
> Paste this entire prompt into a fresh Claude Code session. Phase 0 must be complete and golden fixtures saved before starting this phase.

---

Phase 0 is complete. The Critic agent is validated and all golden fixtures are saved in `data/golden_fixtures/`. Now build the core OpenEnv environment with two reward signals and get a complete dummy episode running end-to-end.

**Current state:**
- `agents/critic.py` — CriticAgent working and validated
- `data/golden_fixtures/` — 10 validated critic outputs as JSON
- `data/test_scripts/scripts.json` — 10 test scripts

---

## New files to create

```
viral_script_engine/
├── environment/
│   ├── __init__.py
│   ├── env.py
│   ├── actions.py
│   ├── observations.py
│   └── episode_state.py
├── rewards/
│   ├── __init__.py
│   ├── base.py
│   ├── r1_hook_strength.py
│   ├── r2_coherence.py
│   └── reward_aggregator.py
├── agents/
│   └── rewriter.py          # NEW — do not modify critic.py
├── tests/
│   ├── test_environment.py
│   └── test_rewards.py
└── scripts/
    └── run_dummy_episode.py
```

**The environment must follow OpenEnv's Gymnasium-compatible API exactly:**
- `reset()` → `(observation: dict, info: dict)`
- `step(action)` → `(observation: dict, reward: float, terminated: bool, truncated: bool, info: dict)`
- `state()` → full current state dict

---

## Step 1 — `environment/actions.py`

```python
from enum import Enum
from pydantic import BaseModel

class ActionType(str, Enum):
    HOOK_REWRITE = "hook_rewrite"
    SECTION_REORDER = "section_reorder"
    CULTURAL_REF_SUB = "cultural_ref_sub"
    CTA_PLACEMENT = "cta_placement"

class ArbitratorAction(BaseModel):
    action_type: ActionType
    target_section: str      # "hook" | "body" | "cta" | "full"
    instruction: str         # natural language instruction to the Rewriter
    critique_claim_id: str   # which CritiqueClaim this responds to, e.g. "C2"
    reasoning: str           # why this action was chosen (used in demo and logs)
```

---

## Step 2 — `environment/observations.py`

```python
class RewardComponents(BaseModel):
    r1_hook_strength: Optional[float] = None
    r2_coherence: Optional[float] = None
    r3_cultural_alignment: Optional[float] = None
    r4_debate_resolution: Optional[float] = None
    r5_defender_preservation: Optional[float] = None
    r6_retention_proxy: Optional[float] = None
    anti_gaming_penalty: float = 0.0
    total: float = 0.0

    def compute_total(self) -> float:
        # Weights: R1=0.25, R2=0.20, R3=0.20, R4=0.20, R5=0.15
        # Sum only non-None components, normalise weights to sum to 1.0
        # Subtract anti_gaming_penalty, clip to [0, 1]

class DebateRound(BaseModel):
    step_num: int
    critic_claims: List[CritiqueClaim]
    defender_response: Optional[Any] = None   # DefenderOutput added in Phase 2
    arbitrator_action: Optional[ArbitratorAction] = None
    rewrite_diff: Optional[str] = None        # unified diff string
    reward_components: Optional[RewardComponents] = None

class Observation(BaseModel):
    current_script: str
    original_script: str
    region: str
    platform: str
    niche: str
    step_num: int
    max_steps: int
    debate_history: List[DebateRound]
    reward_components: RewardComponents
    difficulty_level: str   # "easy" | "medium" | "hard" | "self_generated"
    episode_id: str         # UUID
```

---

## Step 3 — `rewards/r1_hook_strength.py`

Fully rule-based — zero LLM calls. Scores the first 3 sentences or ~50 words (whichever is shorter).

**5 checks, each worth 0.2:**

1. **Promise check** — hook contains a concrete promise or specific claim. Look for: numbers, "how to", "why", "what happens when", "I made X". Fail: generic openers like "Hey guys", "Welcome back", "Today we're talking about".

2. **Curiosity gap check** — hook creates unresolved tension. Look for: question structures, "but here's the thing", "most people don't know", "the secret is". Fail: hook that immediately resolves the tension in the same sentence.

3. **Specificity check** — at least one specific number, proper noun, or concrete detail. Look for: digit sequences, proper nouns, specific product/place names.

4. **Front-loading check** — first sentence contains at least 2 of the above signals.

5. **Anti-filler check** — avoids these dead openers (case-insensitive): `["hey guys", "welcome back", "today i want to", "so today", "in this video", "what's up everyone", "hey everyone", "guys today", "hello everyone", "so basically"]`

`score = checks_passed / 5`, clipped to [0, 1].

Return a `HookRewardResult` with: `score`, `checks_passed`, `check_details: dict`.

---

## Step 4 — `rewards/r2_coherence.py`

Uses `sentence-transformers all-MiniLM-L6-v2`. Cache embeddings by `hash(text)`.

Score mapping from raw cosine similarity:
- `< 0.65` → `0.0` (drifted too far from creator intent)
- `0.65–0.80` → linearly map to `0.0–0.5`
- `0.80–0.95` → linearly map to `0.5–1.0`
- `> 0.95` → `0.8` (barely changed — penalise inaction)

Return a `CoherenceRewardResult` with: `score`, `raw_similarity`, `interpretation: str`.

---

## Step 5 — `rewards/reward_aggregator.py`

```python
class RewardAggregator:
    WEIGHTS = {"r1": 0.25, "r2": 0.20, "r3": 0.20, "r4": 0.20, "r5": 0.15}

    def compute(
        self,
        components: RewardComponents,
        episode_start_components: RewardComponents,
        action_history: List[ActionType],
    ) -> RewardComponents:
```

**Anti-gaming rule 1 — Catastrophic drop:**
For each reward component not None in both current and episode_start: if `current < episode_start - 0.2`, set total = 0.0 and log which component triggered it.

**Anti-gaming rule 2 — Action diversity:**
If the last 3 entries in `action_history` are all the same `ActionType`, subtract 0.15 from total before clipping.

Always clip final total to [0, 1]. Set `components.anti_gaming_penalty` to total deduction applied.

---

## Step 6 — `agents/rewriter.py`

```python
class RewriterAgent:
    def __init__(self, model_name: str = "claude-sonnet-4-20250514"):
        pass

    def rewrite(self, current_script: str, action: ArbitratorAction) -> RewriteResult:
        pass
```

System prompt: "You are a professional script editor for short-form social media video. Apply ONLY the instruction given. Do not make any other changes. Do not add new ideas. Do not change the creator's voice or regional language patterns. Return ONLY the rewritten script text, no commentary."

User prompt includes: `current_script`, `action.action_type`, `action.instruction`, `action.target_section`.

`RewriteResult` has: `rewritten_script`, `diff` (unified diff string), `word_count_delta: int`.

---

## Step 7 — `environment/env.py`

```python
from openenv import Environment

class ViralScriptEnv(Environment):
    DIFFICULTY_LEVELS = ["easy", "medium", "hard", "self_generated"]

    def __init__(
        self,
        scripts_path: str = "data/test_scripts/scripts.json",
        max_steps: int = 5,
        difficulty: str = "easy",
        use_anti_gaming: bool = True,
    ):
        # Script tiers: easy=S01-S04, medium=S05-S07, hard=S08-S10
        # Init: CriticAgent, RewriterAgent, RewardAggregator, HookStrengthReward, CoherenceReward
        # R3-R5 are None until Phase 2

    def reset(self, seed=None, options=None) -> Tuple[dict, dict]:
        # 1. Sample script from current difficulty tier
        # 2. Reset all debate state
        # 3. Compute initial R1 and R2 on unmodified script → save as episode_start_rewards
        # 4. Return (observation_dict, info_dict)

    def step(self, action: dict) -> Tuple[dict, float, bool, bool, dict]:
        # 1. Parse action dict → ArbitratorAction
        # 2. Run Critic on current script
        # 3. [Defender: skip in Phase 1, wire in Phase 2]
        # 4. Run Rewriter with the action → new script
        # 5. Compute R1, R2 on new script
        # 6. Run RewardAggregator (anti-gaming checks applied)
        # 7. Append DebateRound to debate_history
        # 8. Increment step counter
        # 9. terminated if step_num >= max_steps OR total_reward >= 0.9
        # 10. info_dict must include: reward_components, anti_gaming_triggered, penalty_reason

    def state(self) -> dict:
        # Full JSON-serialisable state: current_script, original_script, debate_history,
        # reward_components, step_num, difficulty_level, episode_id
```

---

## Step 8 — `scripts/run_dummy_episode.py`

```
python scripts/run_dummy_episode.py --difficulty easy --steps 3 --verbose
```

1. Instantiate `ViralScriptEnv`
2. Call `reset()`
3. Each step: sample a random `ActionType`, construct a minimal valid `ArbitratorAction`, call `step()`
4. Print per-step: script diff, reward components, any anti-gaming penalties (use `rich` panels/tables)
5. At end: print final reward, R1, R2
6. Save full episode log to `logs/episode_<id>.json`

Output must be readable to a non-technical judge watching the demo.

---

## Step 9 — Tests

**`tests/test_environment.py`:**
- `reset()` returns a valid observation dict
- `step()` with a valid action completes without error
- `step()` increments `step_num` correctly
- Anti-gaming penalty fires when same action repeated 3 times
- Episode terminates at `max_steps`
- Reward is clipped to [0, 1]
- Mock all LLM calls using fixtures from `data/golden_fixtures/`

**`tests/test_rewards.py`:**
- R1 on 5 hand-crafted hooks: 2 score >0.8, 2 score <0.3, 1 is edge case ~0.5
- R2 with identical strings → 0.8 (the >0.95 penalty case)
- R2 with completely different strings → 0.0 (below 0.65 threshold)
- RewardAggregator catastrophic drop penalty zeroes reward correctly
- RewardAggregator diversity penalty fires on 3 identical consecutive actions

---

## Gate check

Run:
```
python scripts/run_dummy_episode.py --difficulty easy --steps 3 --verbose
```

The final line must print:
```
PHASE 1 GATE: PASS
```

Conditions: (a) episode completed without error, (b) R1 and R2 are non-null in final state, (c) episode log saved to `logs/`.

Also deploy this version to HF Spaces immediately as an early checkpoint before moving to Phase 2.