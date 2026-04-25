# Claude Code Prompts — Index
## Viral Script Debugging Engine · Meta × OpenEnv Hackathon

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

- Use the **Anthropic Python SDK** only (not OpenAI)
- All models/dataclasses use **Pydantic** for validation
- LLM calls only in: CriticAgent, DefenderAgent, RewriterAgent, BaselineArbitratorAgent, CriticEscalationEngine
- Evaluators and reward scorers (R1, R3) are **purely rule-based — zero LLM calls**
- Store API key in `.env`, load with `python-dotenv`
- Use `rich` for all console output
- Mock all Anthropic API calls in tests — no real API calls in the test suite
- Model saving: always use `save_pretrained_merged`, never naive upcast from 4-bit