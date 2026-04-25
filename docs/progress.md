# Progress — Feature & Phase Status

## Purpose
Read this file to know exactly what is done, in progress, or pending.
One liner per feature. Update after every feature implementation.
Do not read entire codebase to understand progress — read this file.

---

## Status Legend

✅ done        — implemented, tested, committed
🔄 in progress — currently being worked on
⏳ pending     — not started yet
❌ blocked     — cannot proceed, reason noted
🐛 bug         — implemented but has known failing test

---

## Phase 1 — OpenEnv Scaffold
✅ ViralScriptEnv — Gym-compatible env with reset/step/state
✅ EpisodeState — dataclass tracking script, region, platform, niche
✅ Rewards R1–R5 — hook strength, coherence, cultural, debate, preservation
✅ RewardAggregator — anti-gaming penalties (action diversity, regression, cliff)
✅ CriticAgent — LLM critique with JSON extraction
✅ DefenderAgent — LLM defense with JSON extraction
✅ RewriterAgent — LLM rewrite from arbitrator action
✅ BaselineArbitratorAgent — zero-shot untrained arbitrator

## Phase 2 — Baseline Measurement
✅ run_baseline.py — 20-episode baseline run, saves baseline_results.json
✅ baseline_reward_curves.png — pre-training reward plot saved
✅ Phase 2 gate — mean total reward logged, curves confirmed saved

## Phase 3 — Curriculum Dataset + GRPO Training
✅ generate_synthetic_scripts.py — Anthropic API script generator (run separately)
✅ build_curriculum.py — 3 JSONL tiers (easy 10, medium 10, hard 5; grows with synthetic)
✅ env.reset_from_config() — resets env from specific episode config dict
✅ rollout_function.py — TRL GRPOTrainer bridge to live ViralScriptEnv
✅ build_training_prompts() — loads JSONL tier into prompt list with embedded config headers
✅ train_grpo.py — GRPO training script with --dry-run, --tier, --steps, --model flags
✅ reward_curves.py — plot_training_curves() 2×3 subplot comparison (baseline vs trained)
✅ eval_trained_model.py — 20-episode eval with trained model, calls plot_training_curves
✅ test_training_pipeline.py — 7 pass, 1 skipped (GRPOConfig blocked by pyarrow DLL on Windows)
✅ Phase 3 gate — dry-run 5 steps, PHASE 3 GATE: PASS printed

## Phase 4 — Critic Escalation Engine (Self-Improvement)
✅ DifficultyTracker — tracks mastery per critique class, persistence, consecutive resolutions
✅ CriticEscalationEngine — generates harder LLM challenges when class is mastered
✅ env.py updated — use_escalation flag, wires tracker/engine into reset() and step()
✅ run_escalation_demo.py — 10/50-episode demo, chart, progression JSON
✅ test_escalation.py — 6 tests, all passing (mastery logic, escalation, integration, JSON)
✅ logs/escalation_chart.png — difficulty vs R4 score dual-axis chart
✅ logs/escalation_progression.json — per-episode and aggregate progression data
✅ Phase 4 gate — PHASE 4 GATE: PASS printed, 10 episodes error-free

## Phase 5 — [Pending]
⏳ Full GRPO training — needs GPU compute credits

## Phase 5 — [Pending]
⏳ [feature name] — [one line description]

## Phase 6 — [Pending]
⏳ [feature name] — [one line description]

## Phase 7 — [Pending]
⏳ [feature name] — [one line description]

## Phase 8 — [Pending]
⏳ [feature name] — [one line description]

---

## Blocked Items
❌ GRPOConfig test — blocked by: pyarrow DLL blocked by Windows App Control (works on Linux/Colab)
❌ Full GRPO training — blocked by: no local GPU (requires Colab or cloud compute)

---

## Rules for This File
- One line per feature, no paragraphs
- Update status after every feature, not at end of phase
- Never delete a line — only update its status
- If blocked, note the reason inline
