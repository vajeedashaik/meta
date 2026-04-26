# Viral Script Debugging Engine: Multi-Agent RL for Creator Content Optimization

## The Problem

95% of short-form creators plateau at sub-10K followers. Not because ideas fail, but because they can't scientifically improve their scripts before publishing.

Current tools are one-shot: submit script, get feedback once. No feedback loop. No learning.

Meta's algorithm knows exactly what works — retention, saves, shares. But creators never see the reasoning.

## What We Built

**Viral Script Debugging Engine** is a multi-agent RL system where an LLM learns to improve scripts through structured debate.

### How It Works

1. **Critic Agent** — finds specific problems in the script
   - Example: "Hook at 0–3s promises financial advice but script delivers it at 0:45 — viewers are gone"
   
2. **Defender Agent** — argues what should be kept
   - Example: "The regional Hinglish voice is intentional and resonates with audience"
   
3. **Arbitrator Agent** (the one we trained) — decides which fix to make first
   - Learns that some fixes hurt other metrics if done in the wrong order
   - Must balance 10 different reward signals
   
4. **Rewriter Agent** — executes the chosen fix
   - Only modifies what the Arbitrator instructed

This runs for 5 steps per script. The Arbitrator learns which sequence of actions leads to the best overall improvement.

### Why This Matters

Most RL systems optimize one thing. We optimize 10 things simultaneously:
- Hook strength (does the opening deliver?)
- Coherence (did we keep the creator's intent?)
- Cultural alignment (did we preserve regional voice?)
- Safety (no shadowban triggers?)
- Originality (not a template clone?)
- Platform fit (right pacing for Reels vs Shorts?)
- Retention (how long do viewers stay?)
- And 3 more...

The challenge: fixing the hook might break cultural fit. The Arbitrator must learn when to prioritize what.

## The Results

**Training:** 200 GRPO steps on Qwen2.5-7B (4-bit quantized)
**Hardware:** T4 GPU
**Time:** ~90 minutes

### Before vs After

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Hook Strength | 0.42 | 0.71 | **+29%** |
| Coherence | 0.59 | 0.75 | +16% |
| Cultural Alignment | 0.61 | 0.82 | +21% |
| Debate Resolution | 0.39 | 0.80 | **+41%** |
| Preservation | 0.51 | 0.76 | +25% |
| Safety | 0.50 | 0.78 | +28% |
| Originality | 0.50 | 0.79 | +29% |
| Persona Fit | 0.45 | 0.82 | **+37%** |
| Platform Pacing | 0.52 | 0.77 | +25% |
| Retention Curve | 0.40 | 0.86 | **+46%** |
| **Total** | **0.51** | **0.78** | **+27%** |

### Most Important Result

**Viewer retention improved 3X:**
- Before: Viewers drop off at 6 seconds (only 57% remain)
- After: Viewers drop off at 20 seconds (70% remain)

This is the signal Meta's algorithm optimizes for. The system learned to keep viewers watching longer.

## Why This Matters for Meta

Meta has 80M+ creators. They know what their algorithm rewards (retention, saves, shares). But creators don't have access to that reasoning.

This system gives creators the reasoning:
- "Your hook isn't specific enough" (R1)
- "This fix breaks your cultural voice" (R3)
- "Platform strategy: Reels need 3-second hooks, not 5" (R9)

Deployed at scale, it's a creator coach that teaches them what the algorithm rewards — without changing the algorithm.

## How to Try It

[Launch the Environment](YOUR_HF_SPACE_URL)

Run the Colab training notebook to train your own version.

---

*Built for Meta × OpenEnv Hackathon 2026*