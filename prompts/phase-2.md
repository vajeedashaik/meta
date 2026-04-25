# Phase 2 — Defender Agent + R3/R4/R5 + Anti-Gaming + Baseline
> Paste this entire prompt into a fresh Claude Code session. Phase 1 must be complete (dummy episode running, R1/R2 working) before starting.

---

Phase 1 is complete. The environment scaffold runs and dummy episodes complete end-to-end. Now complete the full agent loop with all 5 reward signals, bake in the anti-gaming protections with full logging, and record the pre-training baseline.

**Current state:**
- `environment/env.py` — ViralScriptEnv working with R1+R2
- `agents/critic.py` — validated CriticAgent
- `agents/rewriter.py` — RewriterAgent
- Defender slot exists in Observation but is still `None`

---

## Step 1 — `agents/defender.py`

```python
class DefenderOutput(BaseModel):
    core_strength: str              # single most important thing to preserve
    core_strength_quote: str        # exact verbatim quote from the script
    defense_argument: str           # why this should not be changed
    flagged_critic_claims: List[str]    # claim_ids the Defender believes are overcorrections
    regional_voice_elements: List[str]  # phrases/references that are intentionally regional

class DefenderAgent:
    def __init__(self, model_name: str = "claude-sonnet-4-20250514"):
        pass

    def defend(
        self,
        script: str,
        critic_claims: List[CritiqueClaim],
        region: str,
        platform: str,
    ) -> DefenderOutput:
        pass
```

**System prompt (exact):**
```
You are a script defender for short-form video content. Your job is NOT to say the script is perfect.
Your job is to identify what is genuinely working — and protect it from being edited away.

Specifically:
1. Find the single most powerful element of the script. Quote it exactly.
2. Explain why a viewer would respond positively to this element.
3. Review the Critic's claims. Flag any that would destroy the script's core strength or strip its regional authenticity if acted on.
4. List any phrases, idioms, or references that are intentionally regional — these must not be "corrected" away.

OUTPUT (JSON only, no preamble):
{
  "core_strength": "one sentence describing the strongest element",
  "core_strength_quote": "exact verbatim quote from the script",
  "defense_argument": "why this element should be preserved",
  "flagged_critic_claims": ["C2", "C3"],
  "regional_voice_elements": ["specific phrase 1", "specific phrase 2"]
}
```

---

## Step 2 — `rewards/r3_cultural_alignment.py`

Rule-based, zero LLM calls. Uses a JSON knowledge base.

```python
class CulturalAlignmentReward:
    def __init__(self, knowledge_base_path: str = "data/cultural_kb.json"):
        pass

    def score(self, script: str, region: str) -> CulturalRewardResult:
        # score = (valid_refs_found + correct_idioms_found
        #          - invalid_signals_found - anachronistic_signals_found)
        #         / max(total_valid_refs + total_idioms, 1)
        # clip to [0, 1]
```

Create `data/cultural_kb.json` with at least 15 entries per category per region for:

**Mumbai Gen Z:**
- `valid_refs`: Bandra, CSMT, dabba, auto, local train, startup scene, Zomato, Swiggy, IPL, Bollywood 2020s
- `invalid_signals`: outdated slang pre-2015
- `correct_idioms`: "ek dum solid", "full on", "kya scene hai", Hinglish patterns

**Tier-2 Hindi Belt:**
- `valid_refs`: kirana store, mandap, jugaad, sabzi mandi, panchayat, mela, dal-chawal
- `invalid_signals`: metro-centric language, startup jargon
- `correct_idioms`: Hindi-dominant mixed phrases

**Pan-India English:** minimal constraints; penalise overly regional without context.

**Hinglish:** reward balanced Hindi-English mixing; penalise fully formal English.

---

## Step 3 — `rewards/r4_debate_resolution.py`

Re-runs the Critic on the new script after each rewrite. Checks whether the specific claim the Arbitrator targeted still appears.

```python
class DebateResolutionReward:
    def __init__(self, critic_agent: CriticAgent):
        self.critic = critic_agent

    def score(
        self,
        new_script: str,
        original_action: ArbitratorAction,
        original_claim: CritiqueClaim,
        region: str,
        platform: str,
        niche: str,
    ) -> DebateResolutionResult:
        # Re-run critic on new_script
        # A claim is "resolved" if new critique has NO claim of the same critique_class
        #   targeting the same timestamp_range (±5 seconds)
        # OR the new claim for that section has severity "low" (down from "medium"/"high")
        # Score: 1.0=resolved, 0.5=partially resolved (severity reduced), 0.0=claim persists
```

---

## Step 4 — `rewards/r5_defender_preservation.py`

Uses `sentence-transformers all-MiniLM-L6-v2` (same model as R2 — reuse the loaded instance).

```python
class DefenderPreservationReward:
    def score(self, defender_output: DefenderOutput, rewritten_script: str) -> DefenderPreservationResult:
        # Chunk rewritten_script into sentences
        # Compute cosine_similarity(embed(core_strength_quote), embed(sentence)) for each sentence
        # Take the max similarity across all sentences
        # Score mapping:
        #   max_similarity >= 0.85 → 1.0
        #   max_similarity 0.65–0.85 → max_similarity (partial)
        #   max_similarity < 0.65 → 0.0
```

---

## Step 5 — Update `environment/env.py`

**Modify `step()`:**
1. After Critic runs, immediately run Defender on the same script state
2. Store `DefenderOutput` in the `DebateRound`
3. After Rewriter executes, compute R3, R4, R5 alongside R1, R2
4. Pass all 5 to RewardAggregator

**Modify `reset()`:**
1. Compute baseline R1–R5 on unmodified script at episode start
2. R4 and R5 will be `None` at reset — handle gracefully in aggregator (skip them in weighted sum)

---

## Step 6 — Update `rewards/reward_aggregator.py`

- Anti-gaming catastrophic drop check must now work across all 5 rewards
- Normalise weights so available (non-None) rewards always sum to 1.0

Add `AntiGamingLog`:

```python
class AntiGamingLog(BaseModel):
    episode_id: str
    step_num: int
    triggered: bool
    rule_triggered: Optional[str]         # "catastrophic_drop" | "action_repetition" | None
    component_that_dropped: Optional[str] # which reward triggered catastrophic drop
    penalty_applied: float
    pre_penalty_total: float
    post_penalty_total: float
```

Every `RewardAggregator.compute()` call must return `(RewardComponents, AntiGamingLog)`. Save all `AntiGamingLog` entries in the episode's `info` dict and in the episode log JSON.

---

## Step 7 — `agents/baseline_arbitrator.py`

```python
class BaselineArbitratorAgent:
    """
    Untrained Arbitrator for the pre-training baseline.
    Uses zero-shot instruction — no chain-of-thought, no few-shot examples.
    This ensures the comparison is fair: trained model learns through RL, not prompting.
    """

    SYSTEM_PROMPT = """
    You are helping improve a short-form video script.
    You have observed a debate between a Critic and a Defender about the script.
    Choose ONE action to take to improve the script.

    Available actions: hook_rewrite, section_reorder, cultural_ref_sub, cta_placement

    Respond ONLY with valid JSON:
    {
      "action_type": "hook_rewrite",
      "target_section": "hook",
      "instruction": "specific instruction for the rewriter",
      "critique_claim_id": "C1",
      "reasoning": "brief explanation"
    }
    """

    def __init__(self, model_name: str = "claude-haiku-4-5-20251001"):
        # Haiku: cheaper and clearly weaker than trained model
        pass

    def act(self, observation: dict) -> dict:
        pass
```

---

## Step 8 — `scripts/run_baseline.py`

Run 20 full episodes with `BaselineArbitratorAgent`:
- Episodes 1–8: `difficulty="easy"`
- Episodes 9–16: `difficulty="medium"`
- Episodes 17–20: `difficulty="hard"`

Log per episode: episode_id, difficulty, script_id, per-step R1–R5, anti_gaming_triggered, penalty, total reward, final script vs original.

Save to `logs/baseline_results.json`.

Generate `logs/baseline_reward_curves.png`:
- 2 rows × 3 cols subplots: R1, R2, R3, R4, R5, Total
- X-axis: episode number (1–20), labelled
- Y-axis: reward value [0, 1], labelled
- Title: "Baseline (Untrained) Arbitrator — Pre-Training Reward Curves"
- `dpi=150`, save as PNG
- These plots are submitted to judges

Print a `rich` summary table showing mean ± std of each reward across all 20 episodes.

---

## Step 9 — `tests/test_phase2.py`

- `DefenderAgent` parses output correctly from mock LLM response
- R3 scores correctly on 3 regional vs 3 non-regional hand-crafted scripts
- R4 correctly identifies resolved vs unresolved claims (mock Critic re-run)
- R5 scores correctly when `core_strength_quote` is present vs absent in rewrite
- Anti-gaming catastrophic drop zeroes reward when R2 drops by 0.25
- Anti-gaming diversity penalty fires on 3× same action
- `AntiGamingLog` is populated correctly in both triggering and non-triggering cases

---

## Gate check

Run:
```
python scripts/run_baseline.py
```

Must:
1. Complete all 20 episodes without error
2. Save `logs/baseline_reward_curves.png`
3. Print:
   ```
   PHASE 2 GATE: PASS — Baseline curves saved. Pre-training mean total reward: X.XX
   ```

Expected baseline total reward: **0.25–0.55**. If above 0.7, tasks are too easy. If below 0.1, tasks are too hard and RL training will stall — adjust script difficulty before Phase 3.