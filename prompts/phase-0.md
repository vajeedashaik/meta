# Phase 0 — Critic Quality Gate
> Paste this entire prompt into a fresh Claude Code session. Do not proceed to Phase 1 until the gate check at the bottom passes.

---

You are helping me build a multi-agent RL environment called the "Viral Script Debugging Engine" for the Meta × OpenEnv Hackathon. Before any environment code is written, we need to validate that the Critic agent produces high-quality, adversarial output — because the entire RL loop depends on it.

**Project context:**
- The system trains an LLM (the Arbitrator) via GRPO to decide which script improvements to make
- A Critic agent attacks creator scripts with specific, falsifiable claims
- A Defender agent argues for what should be preserved
- The Arbitrator (RL-trained model) decides which critique to act on each step
- If the Critic produces vague output, the RL signal collapses

**Your task for this phase:** Build the Critic agent and an evaluation harness to validate its output quality before any other code is written.

---

## Directory structure to create

```
viral_script_engine/
├── agents/
│   ├── __init__.py
│   └── critic.py
├── data/
│   ├── test_scripts/
│   └── golden_fixtures/
├── evaluation/
│   ├── __init__.py
│   └── critic_evaluator.py
├── scripts/
│   └── run_critic_gate.py
├── requirements.txt
└── README.md
```

---

## Step 1 — `agents/critic.py`

Implement a `CriticAgent` class:

```python
class CriticAgent:
    def __init__(self, model_name: str = "claude-sonnet-4-20250514"):
        # Use the Anthropic Python SDK
        
    def critique(self, script: str, region: str, platform: str, niche: str) -> CritiqueOutput:
        # Returns a CritiqueOutput dataclass
```

The `CritiqueOutput` and `CritiqueClaim` Pydantic models must have these exact fields:

```python
class CritiqueClaim(BaseModel):
    claim_id: str           # e.g. "C1", "C2"
    critique_class: str     # one of: "hook_weakness" | "pacing_issue" | "cultural_mismatch" | "cta_buried" | "coherence_break" | "retention_risk"
    claim_text: str
    timestamp_range: str    # e.g. "0:00-0:03" or "N/A"
    evidence: str           # exact quote from the script supporting this claim
    is_falsifiable: bool
    severity: str           # "low" | "medium" | "high"

class CritiqueOutput(BaseModel):
    claims: List[CritiqueClaim]
    overall_severity: str
    raw_response: str
```

**System prompt to use (exact):**
```
You are an expert social media content critic specialising in short-form video scripts for Reels and YouTube Shorts. Your job is to find specific, real problems in creator scripts — not vague feedback.

RULES:
1. Every claim must cite a specific part of the script (quote it or reference the timestamp range)
2. Every claim must be falsifiable — a human editor must be able to verify it by re-reading the script
3. Never say "the hook is weak" — say "the hook at 0:00-0:03 promises [X] but the script delivers [Y] at 0:22, by which time most viewers have already dropped off"
4. Focus on the 6 critique classes: hook_weakness, pacing_issue, cultural_mismatch, cta_buried, coherence_break, retention_risk
5. Produce between 3 and 6 claims per script. No more, no less.
6. For each claim, assign a timestamp range if the issue is locatable in the script. Use "N/A" only if it's a structural issue spanning the whole script.

OUTPUT FORMAT (respond ONLY with valid JSON, no markdown, no preamble):
{
  "claims": [
    {
      "claim_id": "C1",
      "critique_class": "hook_weakness",
      "claim_text": "...",
      "timestamp_range": "0:00-0:03",
      "evidence": "exact quote from script",
      "is_falsifiable": true,
      "severity": "high"
    }
  ],
  "overall_severity": "high"
}
```

User prompt format:
```
SCRIPT TO CRITIQUE:
{script}

TARGET REGION: {region}
PLATFORM: {platform}
NICHE: {niche}

Produce your critique now.
```

If JSON parsing fails, retry once with a stricter prompt. If it fails twice, raise `CriticParseError`.

---

## Step 2 — `data/test_scripts/scripts.json`

Create 10 realistic 60–90 second Reel/Shorts scripts saved as a JSON array. Distribution:
- S01–S03: Mumbai Gen Z (finance, fashion, tech)
- S04–S06: Tier-2 Hindi belt (agriculture, small business, local culture)
- S07–S08: Pan-India English (startup advice, productivity)
- S09–S10: Hinglish (mixed Hindi-English)

Each entry:
```json
{
  "script_id": "S01",
  "region": "Mumbai Gen Z",
  "platform": "Reels",
  "niche": "personal finance",
  "script_text": "...(100-200 words)...",
  "known_flaws": ["buried_hook", "no_cta"]
}
```

S01–S04 should have **obvious** single flaws. S05–S07 should have **subtle** flaws. S08–S10 should have **conflicting** issues where fixing one hurts another. Do not make all scripts bad in the same way.

---

## Step 3 — `evaluation/critic_evaluator.py`

```python
class CriticEvaluator:
    def evaluate(self, output: CritiqueOutput, script_text: str) -> EvaluationResult:
        pass

    def batch_evaluate(self, results: List[Tuple[CritiqueOutput, str]]) -> BatchEvaluationResult:
        pass
```

`EvaluationResult` fields:
- `claim_count: int` — must be 3–6 to pass
- `specificity_score: float` — fraction of claims where `evidence` is a substring of the script (use substring match)
- `falsifiability_score: float` — fraction of claims with `is_falsifiable=True`
- `timestamp_coverage: float` — fraction of claims with a non-"N/A" timestamp_range
- `critique_class_diversity: float` — unique critique_classes / 6
- `passes_gate: bool` — True if: `claim_count >= 3 AND specificity_score >= 0.6 AND falsifiability_score >= 0.7`

`BatchEvaluationResult` fields:
- `pass_count: int`
- `pass_rate: float`
- `passes_overall_gate: bool` — True if `pass_rate >= 0.8`
- `per_script_results: List[EvaluationResult]`
- `failing_scripts: List[str]`

The evaluator must be purely rule-based — no LLM calls.

---

## Step 4 — `scripts/run_critic_gate.py`

CLI that:
1. Loads all 10 scripts from `data/test_scripts/scripts.json`
2. Runs CriticAgent on each
3. Runs CriticEvaluator on each result
4. Prints a per-script pass/fail report using `rich`
5. Prints overall GATE PASS or GATE FAIL
6. If gate passes: saves all outputs as JSON to `data/golden_fixtures/fixture_S01.json` etc.
7. If gate fails: prints which scripts failed and which scores were below threshold

Flags:
- `--max-retries 3`: retry failed scripts up to N times with a tighter prompt
- `--dry-run`: run only first 2 scripts

---

## Step 5 — `requirements.txt`

```
anthropic>=0.40.0
sentence-transformers>=2.7.0
numpy>=1.26.0
pydantic>=2.0.0
python-dotenv>=1.0.0
rich>=13.0.0
pytest>=8.0.0
```

---

## Step 6 — `tests/test_critic.py`

- Test `CritiqueOutput` parses correctly from a mock LLM JSON response
- Test `EvaluationResult` correctly identifies a passing vs failing critique
- Test CLI exits with code 1 if gate fails, 0 if gate passes
- Mock all Anthropic API calls — no real API calls in tests

---

## Constraints

- Use the Anthropic Python SDK only (not OpenAI)
- Store API key in `.env`, load with `python-dotenv`
- All models use Pydantic for validation
- Evaluator has zero LLM calls
- Use `rich` for all console output (progress bars, coloured pass/fail)
- All JSON outputs pretty-printed with `indent=2`

---

## Gate check

Run:
```
python scripts/run_critic_gate.py --dry-run
```

Must print `PHASE 0 GATE: PASS` when 8/10 scripts produce ≥3 specific, timestamped, falsifiable claims. Do not open Phase 1 until this passes.