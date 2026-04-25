# Phase 7 — Process-Aware Reward Shaping
> Paste this entire prompt into a fresh Claude Code session. Phase 6 must be complete before starting.

---

Phase 6 is complete. All 7 reward signals are active. Now implement process-aware reward shaping — the participant guide explicitly asks for this in section 9 and almost no team will implement it.

**The problem with the current reward design:** All rewards fire at the end of each step, after the rewrite is complete. The Arbitrator gets no signal about whether its *reasoning* was good — only whether the *output* was good. This is inefficient: the model has to learn by trial and error what constitutes good reasoning, instead of being directly rewarded for it.

**What this phase adds:** Intermediate reward signals that fire during the Arbitrator's reasoning chain, before it even picks an action. The Arbitrator is rewarded for correctly diagnosing the priority of critiques, not just for making the right final move.

**Why this matters for training:** Steeper reward curves, faster convergence, better sample efficiency. Your before/after comparison plots will look significantly better with process rewards active. This directly serves the 20% judging weight on showing improvement.

---

## New files to create

```
viral_script_engine/
├── rewards/
│   ├── process_reward.py         # NEW
│   └── process_verifier.py       # NEW
├── agents/
│   └── reasoning_parser.py       # NEW
└── tests/
    └── test_phase7.py            # NEW
```

---

## Step 1 — Change the Arbitrator's output format

Currently the Arbitrator outputs a flat action JSON. Extend it to also output explicit reasoning steps before the action. Update the prompt format in `training/rollout_function.py`:

```
<|system|>
You are an expert content strategist acting as an Arbitrator in a script improvement debate.
Before choosing your action, you must reason through the debate explicitly.

OUTPUT FORMAT (JSON only, in this exact order):
{
  "priority_assessment": "which critique is most urgent and why — one sentence",
  "conflict_check": "does acting on this critique risk harming any other reward signal? yes/no + reason",
  "defender_consideration": "is the Defender's flagged concern relevant to this decision? yes/no + reason",
  "action_type": "...",
  "target_section": "...",
  "instruction": "...",
  "critique_claim_id": "...",
  "reasoning": "..."
}
<|end|>
```

The three new fields — `priority_assessment`, `conflict_check`, `defender_consideration` — are the reasoning chain. They are what process rewards score.

---

## Step 2 — `agents/reasoning_parser.py`

Parses the extended Arbitrator output and extracts the reasoning chain for verification.

```python
class ReasoningChain(BaseModel):
    priority_assessment: str
    conflict_check_answer: str      # "yes" or "no"
    conflict_check_reason: str
    defender_consideration_answer: str   # "yes" or "no"
    defender_consideration_reason: str
    action: ArbitratorAction        # the final action, as before

class ReasoningParser:
    """
    Parses the extended Arbitrator JSON output into a ReasoningChain.
    Falls back gracefully if reasoning fields are missing (backward compatible
    with the untrained baseline model which does not produce reasoning fields).
    """

    def parse(self, raw_output: str) -> ReasoningChain:
        # Parse JSON
        # If reasoning fields missing: set them to empty strings (no process reward)
        # If action fields missing: raise ArbitratorParseError
```

---

## Step 3 — `rewards/process_verifier.py`

Verifies whether the Arbitrator's reasoning is correct, using only rule-based checks — no LLM calls.

```python
class ProcessVerifier:
    """
    Checks whether the Arbitrator's reasoning chain is correct BEFORE
    the action is executed. This is process supervision.

    Three checks, each independently scored:
    """

    def verify_priority_assessment(
        self,
        priority_assessment: str,
        critic_claims: List[CritiqueClaim],
        current_reward_components: RewardComponents,
    ) -> float:
        """
        Checks: does the priority_assessment mention the critique_class with
        the highest severity in the current Critic output?

        Score:
        - 1.0: priority_assessment mentions the highest-severity critique_class
        - 0.5: mentions a medium-severity class (not the worst, but not random)
        - 0.0: mentions a low-severity class or is empty

        Use keyword matching — check if the critique_class string appears
        anywhere in the priority_assessment text.
        """

    def verify_conflict_check(
        self,
        conflict_check_answer: str,
        conflict_check_reason: str,
        action: ArbitratorAction,
        current_reward_components: RewardComponents,
        episode_start_components: RewardComponents,
    ) -> float:
        """
        Checks: is the conflict_check answer consistent with the actual risk?

        A conflict exists if: the action_type is "hook_rewrite" AND
        r3_cultural_alignment is currently >= 0.7 (rewriting the hook risks
        losing cultural references). Similarly for other known conflict patterns.

        Known conflict patterns (encode these as rules):
        - hook_rewrite when r3 >= 0.7 → conflict likely (hook often carries cultural refs)
        - section_reorder when r2 <= 0.6 → conflict likely (reordering risks coherence)
        - cultural_ref_sub when r5 <= 0.5 → conflict likely (substitution risks defender's core strength)
        - cta_placement when r1 <= 0.4 → conflict likely (hook not fixed yet, CTA fix premature)

        Score:
        - 1.0: conflict_check_answer matches the rule-based assessment
        - 0.0: conflict_check_answer contradicts the rule-based assessment or is empty
        """

    def verify_defender_consideration(
        self,
        defender_consideration_answer: str,
        defender_consideration_reason: str,
        action: ArbitratorAction,
        defender_output: DefenderOutput,
    ) -> float:
        """
        Checks: if the action targets the same section as the Defender's
        core_strength_quote, did the Arbitrator say defender_consideration = "yes"?

        Score:
        - 1.0: answer is correct (said "yes" when core_strength is in target section,
                said "no" when core_strength is in a different section)
        - 0.0: answer is wrong or empty
        """
```

---

## Step 4 — `rewards/process_reward.py`

```python
class ProcessReward:
    """
    Combines the three process verification scores into a single
    process reward signal that fires BEFORE the rewrite executes.

    Weights:
    - priority_assessment: 0.40 (most important — did it identify the right problem?)
    - conflict_check:       0.35 (second — did it anticipate consequences?)
    - defender_consideration: 0.25 (third — did it respect what should be preserved?)

    The process reward is added to the step reward ALONGSIDE the outcome rewards,
    but with a lower weight (0.15 of total) so outcome still dominates.
    This prevents the Arbitrator from gaming process rewards by producing
    correct-sounding reasoning that leads to bad actions.
    """

    PROCESS_WEIGHT = 0.15   # how much process reward contributes to total step reward

    def __init__(self):
        self.verifier = ProcessVerifier()

    def score(
        self,
        reasoning_chain: ReasoningChain,
        critic_claims: List[CritiqueClaim],
        defender_output: DefenderOutput,
        current_reward_components: RewardComponents,
        episode_start_components: RewardComponents,
    ) -> ProcessRewardResult:
        """
        Returns ProcessRewardResult with:
        - process_score: float 0–1 (weighted average of three checks)
        - priority_score: float (individual check result)
        - conflict_score: float
        - defender_score: float
        - weighted_contribution: float (process_score × PROCESS_WEIGHT)
        """
```

---

## Step 5 — Update `environment/env.py`

In `step()`, add the process reward computation between parsing the action and executing the rewrite:

```python
def step(self, action: dict):
    # 1. Parse action dict → ArbitratorAction (existing)
    # 2. Run Critic (existing)
    # 3. Run Defender (existing)
    # 4. Run Moderation + Originality agents (Phase 6)

    # NEW — Phase 7: parse reasoning chain and compute process reward
    reasoning_chain = self.reasoning_parser.parse(raw_action_output)
    process_result = self.process_reward.score(
        reasoning_chain=reasoning_chain,
        critic_claims=critic_claims,
        defender_output=defender_output,
        current_reward_components=current_components,
        episode_start_components=self._episode_start_rewards,
    )
    # Store process reward in components — it will be added to total by aggregator

    # 5. Run Rewriter (existing)
    # 6. Compute R1–R7 outcome rewards (existing)
    # 7. Run RewardAggregator — now also receives process_result
```

Update `RewardComponents` to include:
```python
process_reward: Optional[float] = None   # fired before rewrite
```

Update `RewardAggregator.compute()` to add `process_result.weighted_contribution` to the total before anti-gaming checks. Process reward is additive — it does not replace outcome rewards.

---

## Step 6 — Update `training/rollout_function.py`

The prompt format must now include the extended output format with reasoning fields. Update the `<|system|>` block to match the new format defined in Step 1.

Also update the response parser in the rollout function to handle the extended JSON. If the model doesn't produce reasoning fields (e.g. early in training), fall back gracefully — the `ReasoningParser` already handles this.

---

## Step 7 — Update `scripts/run_baseline.py`

Re-run the baseline with the new prompt format. The baseline model will likely score 0 on process rewards (it doesn't produce reasoning fields). This is correct — it makes the before/after comparison even more dramatic: the trained model not only makes better decisions, it also shows better reasoning.

Save new baseline results to `logs/baseline_results_v2.json`. Do not overwrite the original baseline.

---

## Step 8 — Update `demo/run_demo.py`

In Act 4 (The Arbitrator Decides), now show the reasoning chain alongside the action:

```
╔══ TRAINED ARBITRATOR ══════════════════════════════════╗
│ Priority: hook_weakness is highest severity (high)     │
│ Conflict check: YES — hook rewrite risks R3 (cultural) │
│ Defender: YES — core strength is in hook section       │
│                                                        │
│ → Action: cultural_ref_sub on hook                     │
│   "Replace generic opener with Mumbai local reference" │
╚════════════════════════════════════════════════════════╝

╔══ UNTRAINED ARBITRATOR ════════════════════════════════╗
│ [No reasoning chain — zero-shot decision]              │
│ → Action: hook_rewrite on hook                         │
│   "Make the hook more engaging"                        │
╚════════════════════════════════════════════════════════╝
```

This makes the reasoning quality difference viscerally clear to non-technical judges.

---

## Step 9 — `tests/test_phase7.py`

- `ReasoningParser` correctly parses full extended JSON
- `ReasoningParser` falls back gracefully when reasoning fields are missing
- `ProcessVerifier.verify_priority_assessment()` correctly scores a high-severity mention (1.0) vs random mention (0.0)
- `ProcessVerifier.verify_conflict_check()` correctly identifies the 4 known conflict patterns
- `ProcessVerifier.verify_defender_consideration()` correctly scores yes/no alignment
- `ProcessReward.score()` produces correct weighted total
- `env.step()` correctly adds process reward to `RewardComponents`
- Process reward does not fire (graceful zero) when reasoning fields are absent

---

## Gate check

Run:
```
python scripts/run_dummy_episode.py --difficulty easy --steps 3 --verbose
```

Must:
1. Show `process_reward` in the reward components output
2. Show the reasoning chain in each DebateRound log
3. Print:
   ```
   PHASE 7 GATE: PASS — Process rewards active. Reasoning chain verified per step.
   ```

Then re-run the baseline script and confirm that the untrained model scores ~0.0 on process rewards while a well-prompted test call scores >0.5. This gap is your training improvement story.