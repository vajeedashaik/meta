# Phase 5 — HF Deployment + Demo Infrastructure
> Paste this entire prompt into a fresh Claude Code session. All environment code (Phases 0–4) must be complete before starting. Training may still be pending — that's fine, it runs onsite.

---

All environment code is complete. Now package everything for HuggingFace Spaces deployment and build the demo infrastructure that will carry 30% of the judging score.

---

## Step 1 — `openenv.yaml`

Create the OpenEnv manifest in the project root:

```yaml
name: viral-script-debugging-engine
version: "1.0.0"
description: >
  A multi-agent RL environment where an LLM Arbitrator learns to improve
  short-form video scripts through adversarial debate. Trains with GRPO via
  HuggingFace TRL + Unsloth. Hits Theme 1 (Multi-Agent) and Theme 4
  (Self-Improvement) simultaneously.
themes:
  - multi_agent_interactions
  - self_improvement
author: "Team Name"
python_requires: ">=3.10"
entry_point: environment.env:ViralScriptEnv
reset_method: reset
step_method: step
state_method: state
reward_method: reward
tools:
  - name: reset
    description: "Start a new script improvement episode"
  - name: step
    description: "Execute one debate round: Critic attacks, Defender responds, Arbitrator acts, Rewriter executes"
  - name: state
    description: "Get current environment state including script, debate history, and reward components"
dependencies:
  - anthropic>=0.40.0
  - sentence-transformers>=2.7.0
  - unsloth
  - trl>=0.12.0
  - numpy>=1.26.0
  - pydantic>=2.0.0
  - fastapi>=0.110.0
  - uvicorn>=0.29.0
```

---

## Step 2 — `app.py` (FastAPI server for HF Spaces)

```python
"""
FastAPI wrapper exposing ViralScriptEnv as an OpenEnv-compliant HTTP server.
Deployed to HuggingFace Spaces on port 7860.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from environment.env import ViralScriptEnv
import uvicorn

app = FastAPI(
    title="Viral Script Debugging Engine",
    description="Multi-agent RL environment for improving short-form video scripts",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_envs: dict = {}   # per-session env instances keyed by session_id

class ResetRequest(BaseModel):
    session_id: str
    difficulty: str = "easy"
    options: dict = {}

class StepRequest(BaseModel):
    session_id: str
    action: dict

@app.post("/reset")
def reset(req: ResetRequest):
    env = ViralScriptEnv(difficulty=req.difficulty)
    obs, info = env.reset(options=req.options)
    _envs[req.session_id] = env
    return {"observation": obs, "info": info}

@app.post("/step")
def step(req: StepRequest):
    env = _envs.get(req.session_id)
    if not env:
        raise HTTPException(404, f"Session {req.session_id} not found. Call /reset first.")
    obs, reward, terminated, truncated, info = env.step(req.action)
    return {"observation": obs, "reward": reward, "terminated": terminated, "truncated": truncated, "info": info}

@app.get("/state/{session_id}")
def state(session_id: str):
    env = _envs.get(session_id)
    if not env:
        raise HTTPException(404, "Session not found")
    return env.state()

@app.get("/health")
def health():
    return {"status": "ok", "environment": "ViralScriptDebugEngine", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
```

---

## Step 3 — `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860

CMD ["python", "app.py"]
```

---

## Step 4 — `demo/run_demo.py`

The flagship demo script — what you run during the pitch. Must tell a 5-act story with `rich` terminal output.

```
python demo/run_demo.py --script S03 --compare    # base vs trained side-by-side
python demo/run_demo.py --interactive             # human acts as Arbitrator
```

**Act 1 — "The Raw Script"**
- Display original script in a `rich` Panel
- Show: region, platform, niche, known flaws

**Act 2 — "The Critic Attacks"**
- Run Critic on the script
- Display each `CritiqueClaim` as a numbered panel, colour-coded by severity (red=high, yellow=medium, green=low)
- 2-second pause between claims for dramatic effect

**Act 3 — "The Defender Responds"**
- Run Defender
- Display `core_strength` in a highlighted box: "WHAT WE MUST PROTECT"
- Show each `flagged_critic_claims` entry with "⚠ Defender flagged this as overcorrection"

**Act 4 — "The Arbitrator Decides"** (both shown when `--compare`)
- Grey panel: "Untrained Arbitrator chose: [action] — Reasoning: [reasoning]"
- Blue panel: "Trained Arbitrator chose: [action] — Reasoning: [reasoning]"
- Highlight the difference in reasoning

**Act 5 — "The Rewrite + Reward"**
- Show rewritten script as unified diff (coloured: green=added, red=removed)
- Show reward components as a progress-bar table:
  ```
  R1 Hook Strength    ██████░░  0.75
  R2 Coherence        ████░░░░  0.60
  R3 Cultural         ███████░  0.85
  R4 Resolution       █████░░░  0.70
  R5 Preservation     ██████░░  0.75
  ─────────────────────────────────
  Total               █████░░░  0.73  (+34% vs baseline)
  ```

---

## Step 5 — `README.md`

Write the complete README with this exact structure:

```markdown
# Viral Script Debugging Engine
### Meta × OpenEnv Hackathon 2026 | Theme 1: Multi-Agent · Theme 4: Self-Improvement

## The Problem
[2 paragraphs: 95% of creators never break 10k. Existing tools are one-shot pipelines, not RL.]

## What We Built
[2 paragraphs: the multi-agent RL loop. NOT a content generator. A reasoning system.]

## How It Works
[Describe the 4-step loop: Critic → Defender → Arbitrator → Rewriter. One episode = one trajectory.]

## Environment API
[Code block showing reset(), step(), state(), reward() with example inputs/outputs]

## Reward Functions
[Table of R1–R5: what each measures and how it's computed]

## Anti-Gaming Protections
[Explain the two rules: catastrophic drop penalty and action diversity penalty]
[Show 2–3 real examples from training logs where penalties fired]

## Self-Improvement Loop (Theme 4)
[Explain the Critic Escalation Engine and Difficulty Tracker]
![Escalation chart](logs/escalation_chart.png)

## Training
Model: Qwen2.5-7B-Instruct | Algorithm: GRPO via TRL + Unsloth
[Link to Colab notebook]

## Results
![Reward improvement](logs/training_vs_baseline.png)
[Table: per-reward improvement, baseline vs trained]

## Why This Matters for Meta
[One paragraph: the Meta business case]

## HuggingFace Space
[Link: huggingface.co/spaces/YOUR_TEAM/viral-script-debugging-engine]

## References
[Links to mini-blog, video demo, Colab notebook]
```

---

## Step 6 — `notebooks/training_colab.ipynb`

Generate a Colab-ready notebook with these cells in order:

```python
# Cell 1 — Install
!pip install unsloth trl anthropic sentence-transformers openenv pydantic rich

# Cell 2 — API key
import os
os.environ["ANTHROPIC_API_KEY"] = "YOUR_KEY_HERE"

# Cell 3 — Dry-run to validate pipeline
!python training/train_grpo.py --dry-run --steps 5

# Cell 4 — Full training
!python training/train_grpo.py --tier easy,medium --steps 200 --model unsloth/Qwen2.5-7B-Instruct-bnb-4bit

# Cell 5 — Evaluate and plot
!python training/eval_trained_model.py

# Cell 6 — Display reward curves inline
from IPython.display import Image
Image("logs/training_vs_baseline.png")

# Cell 7 — Run demo
!python demo/run_demo.py --script S03 --compare
```

---

## Step 7 — `scripts/submission_check.py`

```
python scripts/submission_check.py
```

Prints PASS or FAIL for each requirement:

- `openenv.yaml` exists and parses without error
- `app.py` starts without error (test with a 3-second subprocess timeout)
- README contains `huggingface.co/spaces` link
- `logs/baseline_reward_curves.png` exists
- `logs/training_vs_baseline.png` exists
- `logs/escalation_chart.png` exists
- `notebooks/training_colab.ipynb` exists
- README contains all required sections (The Problem, What We Built, Reward Functions, Anti-Gaming, Results)
- `requirements.txt` is complete
- All tests pass (`pytest` exit code 0)

Final output: `SUBMISSION READY ✓` or `SUBMISSION INCOMPLETE — fix the above before submitting`

---

## Gate check

Run:
```
python scripts/submission_check.py
```

All 10 checks must print PASS. Fix any failures before considering this phase done.

Then run the demo end-to-end once to confirm it tells the full 5-act story without errors:
```
python demo/run_demo.py --script S03 --compare
```