# Claude Code Prompts — Index
## Viral Script Debugging Engine · Meta × OpenEnv Hackathon

---

## ⚠ CORRECTION — Read this before opening any phase file

The phase files (Phase 0–5) incorrectly hardcode `claude-sonnet` and the Anthropic SDK into the agent classes. **Override this everywhere.** The correct architecture is:

### The Arbitrator (the RL-trained model)
This is a **local Qwen model**, trained via GRPO with Unsloth. It never calls any external API. This is the whole point of the project.

```python
# In training/train_grpo.py and rollout_function.py — already correct
model = "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"   # loaded locally via Unsloth
```

### The environment agents (Critic, Defender, Rewriter, Escalation Engine)
These are **also Qwen by default**, loaded locally. The environment is model-agnostic — any backend can be swapped in via config. No API key required to run the environment.

Wherever a phase file says `model_name: str = "claude-sonnet-4-20250514"`, replace with this pattern instead:

```python
# agents/llm_backend.py  — create this once in Phase 0, reuse everywhere
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

class LLMBackend:
    def __init__(self, backend: str = "qwen", model_name: str = "Qwen/Qwen2.5-7B-Instruct"):
        """
        backend: "qwen" | "anthropic" | "openai" | "ollama"
        Default is local Qwen — no API key needed.
        """
        self.backend = backend
        self.model_name = model_name
        if backend == "qwen":
            self.pipe = pipeline("text-generation", model=model_name, device_map="auto")
        elif backend == "anthropic":
            import anthropic
            self.client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY from env
        elif backend == "openai":
            from openai import OpenAI
            self.client = OpenAI()                # reads OPENAI_API_KEY from env

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 512) -> str:
        if self.backend == "qwen":
            messages = [{"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}]
            out = self.pipe(messages, max_new_tokens=max_tokens, return_full_text=False)
            return out[0]["generated_text"]
        elif self.backend == "anthropic":
            msg = self.client.messages.create(
                model=self.model_name, max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            return msg.content[0].text
        elif self.backend == "openai":
            resp = self.client.chat.completions.create(
                model=self.model_name, max_tokens=max_tokens,
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": user_prompt}]
            )
            return resp.choices[0].message.content
```

Every agent class then becomes:

```python
class CriticAgent:
    def __init__(self, backend: str = "qwen", model_name: str = "Qwen/Qwen2.5-7B-Instruct"):
        self.llm = LLMBackend(backend=backend, model_name=model_name)

    def critique(self, script, region, platform, niche) -> CritiqueOutput:
        response = self.llm.generate(CRITIC_SYSTEM_PROMPT, user_prompt)
        # parse JSON as before
```

Same pattern for `DefenderAgent`, `RewriterAgent`, `BaselineArbitratorAgent`, `CriticEscalationEngine`.

### `requirements.txt` — correct version

Replace whatever the phase files specify with:

```
# Core — required
transformers>=4.40.0
torch>=2.2.0
accelerate>=0.28.0
unsloth
trl>=0.12.0
sentence-transformers>=2.7.0
pydantic>=2.0.0
numpy>=1.26.0
python-dotenv>=1.0.0
rich>=13.0.0
fastapi>=0.110.0
uvicorn>=0.29.0
pytest>=8.0.0
matplotlib>=3.8.0
openenv

# Optional — only needed if using non-Qwen backends
anthropic>=0.40.0      # only if backend="anthropic"
openai>=1.0.0          # only if backend="openai"
```

### `.env` file — only needed if using a non-default backend

```
# Only fill in what you're actually using
ANTHROPIC_API_KEY=sk-ant-...   # optional
OPENAI_API_KEY=sk-...          # optional
# No key needed for default Qwen backend
```

### In tests — mock `LLMBackend.generate()`, not the Anthropic SDK

```python
# tests/conftest.py
from unittest.mock import patch

@pytest.fixture
def mock_llm(monkeypatch):
    monkeypatch.setattr("agents.llm_backend.LLMBackend.generate",
                        lambda self, sys, usr, **kw: MOCK_RESPONSE)
```

---

## How to use these files

Each file is a standalone prompt. Open a **fresh Claude Code session** for each phase and paste the entire file contents. Do not trim or summarise — Claude Code needs the full context.

**Do not open the next phase until the gate check at the bottom of the current phase prints PASS.**

---

## Files

| File | Phase | What it builds | Gate command |
|---|---|---|---|
| `phase_0_critic_gate.md` | Phase 0 | Critic agent + evaluation harness + 10 test scripts | `python scripts/run_critic_gate.py --dry-run` |
| `phase_1_openenv_scaffold.md` | Phase 1 | OpenEnv env scaffold + R1/R2 rewards + Rewriter | `python scripts/run_dummy_episode.py --difficulty easy --steps 3 --verbose` |
| `phase_2_defender_rewards_baseline.md` | Phase 2 | Defender + R3/R4/R5 + anti-gaming logging + baseline curves | `python scripts/run_baseline.py` |
| `phase_3_curriculum_grpo_training.md` | Phase 3 | Curriculum datasets + GRPO training pipeline | `python training/train_grpo.py --dry-run` |
| `phase_4_escalation_engine.md` | Phase 4 | Difficulty Tracker + Critic Escalation Engine | `python scripts/run_escalation_demo.py --episodes 10 --verbose` |
| `phase_5_deployment_demo.md` | Phase 5 | FastAPI server + Dockerfile + demo script + README | `python scripts/submission_check.py` |
| `phase_6_moderation_originality.md` | Phase 6 | Moderation Agent + Originality Agent + R6/R7 | `python scripts/run_dummy_episode.py --difficulty easy --steps 3 --verbose` |
| `phase_7_process_rewards.md` | Phase 7 | Process-aware reward shaping + reasoning chain verification | `python scripts/run_dummy_episode.py --difficulty easy --steps 3 --verbose` |
| `phase_8_creator_persona.md` | Phase 8 | Creator Persona Modelling + R8 persona fit | `python scripts/run_dummy_episode.py --difficulty medium --steps 3 --verbose` |
| `phase_9_platform_divergence.md` | Phase 9 | Multi-platform reward divergence + R9 pacing | `python scripts/run_platform_comparison.py --script S03 --platforms Reels,Shorts,Feed` |
| `phase_10_ab_testing.md` | Phase 10 | A/B contrastive environment + delta-based reward | `python scripts/run_ab_episode.py --script S08 --steps 4 --verbose` |
| `phase_11_longitudinal_memory.md` | Phase 11 | Longitudinal episode memory + Creator History Buffer | `python scripts/run_longitudinal_demo.py --creator S01 --sessions 6 --verbose` |
| `phase_12_retention_curve.md` | Phase 12 | Retention Curve Simulator + R10 + sklearn predictor | `python scripts/train_retention_model.py` |

---

## Full file structure after all phases

```
viral_script_engine/
├── agents/
│   ├── critic.py                     # Phase 0
│   ├── defender.py                   # Phase 2
│   ├── rewriter.py                   # Phase 1
│   └── baseline_arbitrator.py        # Phase 2
├── data/
│   ├── test_scripts/scripts.json     # Phase 0
│   ├── golden_fixtures/              # Phase 0
│   ├── cultural_kb.json              # Phase 2
│   └── curriculum/                   # Phase 3
│       ├── easy_tier.jsonl
│       ├── medium_tier.jsonl
│       ├── hard_tier.jsonl
│       └── synthetic_scripts.json
├── environment/
│   ├── env.py                        # Phase 1 (updated Phase 2, 4)
│   ├── actions.py                    # Phase 1
│   ├── observations.py               # Phase 1
│   └── episode_state.py              # Phase 1
├── escalation/
│   ├── difficulty_tracker.py         # Phase 4
│   └── critic_escalation_engine.py   # Phase 4
├── evaluation/
│   └── critic_evaluator.py           # Phase 0
├── rewards/
│   ├── base.py                       # Phase 1
│   ├── r1_hook_strength.py           # Phase 1
│   ├── r2_coherence.py               # Phase 1
│   ├── r3_cultural_alignment.py      # Phase 2
│   ├── r4_debate_resolution.py       # Phase 2
│   ├── r5_defender_preservation.py   # Phase 2
│   └── reward_aggregator.py          # Phase 1 (updated Phase 2)
├── training/
│   ├── rollout_function.py           # Phase 3
│   ├── train_grpo.py                 # Phase 3
│   ├── eval_trained_model.py         # Phase 3
│   └── reward_curves.py              # Phase 3
├── demo/
│   └── run_demo.py                   # Phase 5
├── scripts/
│   ├── run_critic_gate.py            # Phase 0
│   ├── run_dummy_episode.py          # Phase 1
│   ├── run_baseline.py               # Phase 2
│   ├── run_escalation_demo.py        # Phase 4
│   └── submission_check.py           # Phase 5
├── tests/
│   ├── test_critic.py                # Phase 0
│   ├── test_environment.py           # Phase 1
│   ├── test_rewards.py               # Phase 1
│   ├── test_phase2.py                # Phase 2
│   ├── test_training_pipeline.py     # Phase 3
│   └── test_escalation.py           # Phase 4
├── notebooks/
│   └── training_colab.ipynb          # Phase 5
├── logs/                             # generated at runtime
├── outputs/                          # training checkpoints
├── app.py                            # Phase 5
├── openenv.yaml                      # Phase 5
├── Dockerfile                        # Phase 5
├── requirements.txt                  # Phase 0
└── README.md                         # Phase 5
```

---

## Key constraints to keep in mind across all phases

- Default LLM backend is **local Qwen via `transformers`** — no API key required
- All agents use `LLMBackend` (defined in the correction note above) — swappable to any provider
- The RL-trained Arbitrator is always local Qwen via Unsloth — never an API call
- All models/dataclasses use **Pydantic** for validation
- LLM calls only in: CriticAgent, DefenderAgent, RewriterAgent, BaselineArbitratorAgent, CriticEscalationEngine
- Evaluators and reward scorers (R1, R3) are **purely rule-based — zero LLM calls**
- API keys in `.env` are optional — only needed if switching backend away from Qwen
- Use `rich` for all console output
- Mock `LLMBackend.generate()` in tests — no real model calls in the test suite
- Model saving: always use `save_pretrained_merged`, never naive upcast from 4-bit