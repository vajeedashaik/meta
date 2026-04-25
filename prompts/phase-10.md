# Phase 10 — A/B Testing Environment Layer
> Paste this entire prompt into a fresh Claude Code session. Phase 9 must be complete before starting.

---

Phase 9 is complete. Platform-aware rewards are active. Now add the most technically innovative addition in the entire project: a contrastive A/B testing layer that teaches the Arbitrator not just what works, but what *doesn't* — by running counterfactual trajectories in parallel.

**The core idea:** Instead of one linear rewrite trajectory, each episode runs two parallel trajectories from the same starting script. Trajectory A acts on the Critic's top claim first. Trajectory B acts on the Defender's preservation concern first. Both play out for N steps. The reward signal is the *delta* between them — the Arbitrator learns from the counterfactual.

**Why this is genuinely novel RL design:** Standard RL environments give the agent one trajectory and one outcome. Contrastive reward structures — where the agent learns from seeing what the alternative would have produced — are an active research area. Implementing this in a hackathon project puts you at the frontier of RL environment design, not just application of existing patterns.

**Direct Meta parallel:** This is exactly how Meta runs content A/B tests before pushing to the feed. A judge from Meta will immediately recognise this as production-level thinking. The system is learning the same comparative reasoning that Meta's own infrastructure uses.

---

## New files to create

```
viral_script_engine/
├── environment/
│   ├── ab_env.py                 # NEW — A/B environment wrapper
│   └── trajectory.py             # NEW — trajectory state management
├── rewards/
│   └── contrastive_reward.py    # NEW — delta-based reward
├── scripts/
│   └── run_ab_episode.py        # NEW — demo/test script
└── tests/
    └── test_phase10.py           # NEW
```

---

## Step 1 — `environment/trajectory.py`

```python
from pydantic import BaseModel
from typing import List, Optional
from environment.observations import Observation, RewardComponents, DebateRound
from environment.actions import ArbitratorAction

class TrajectoryType(str):
    CRITIC_FIRST = "critic_first"     # Trajectory A: act on Critic's top claim first
    DEFENDER_FIRST = "defender_first" # Trajectory B: act on Defender's concern first

class Trajectory(BaseModel):
    trajectory_id: str
    trajectory_type: str
    initial_script: str
    current_script: str
    steps: List[DebateRound]
    cumulative_reward: float
    final_reward_components: Optional[RewardComponents] = None
    terminated: bool = False
    step_count: int = 0

    def get_forced_first_action(
        self,
        critic_claims: List,
        defender_output,
    ) -> dict:
        """
        Returns the forced first action based on trajectory type.

        CRITIC_FIRST: pick the action that addresses the highest-severity CritiqueClaim
        DEFENDER_FIRST: pick the action that preserves the core_strength_quote
            (if core_strength is in hook → hook_rewrite is risky → pick cta_placement first)
        """
```

---

## Step 2 — `environment/ab_env.py`

```python
from environment.env import ViralScriptEnv
from environment.trajectory import Trajectory, TrajectoryType

class ABScriptEnv:
    """
    A/B Testing wrapper around ViralScriptEnv.

    Each episode runs TWO parallel trajectories from the same starting script:
    - Trajectory A (critic_first): forced to act on Critic's top claim in step 1
    - Trajectory B (defender_first): forced to act on Defender's concern in step 1
    - Steps 2+ are free — the Arbitrator makes its own decisions in both

    The Arbitrator observes BOTH trajectories in the state() output.
    The contrastive reward fires at episode end based on the delta.

    This teaches the Arbitrator: "I could have done X first or Y first.
    One led to a better outcome. Learn which one."
    """

    def __init__(
        self,
        scripts_path: str = "data/test_scripts/scripts.json",
        max_steps: int = 5,
        difficulty: str = "easy",
    ):
        # Create TWO independent ViralScriptEnv instances — one per trajectory
        self.env_a = ViralScriptEnv(scripts_path=scripts_path, max_steps=max_steps, difficulty=difficulty)
        self.env_b = ViralScriptEnv(scripts_path=scripts_path, max_steps=max_steps, difficulty=difficulty)
        self.contrastive_reward = ContrastiveReward()

        self._traj_a: Optional[Trajectory] = None
        self._traj_b: Optional[Trajectory] = None
        self._episode_id: Optional[str] = None

    def reset(self, seed=None, options=None):
        """
        Reset BOTH environments with the SAME script and seed.
        Both trajectories start from identical state.
        Run step 1 automatically with the forced actions:
          - Trajectory A forced action: address highest-severity CritiqueClaim
          - Trajectory B forced action: preserve Defender's core_strength
        Return the state after forced step 1, with both trajectory histories visible.
        """

    def step(self, action: dict):
        """
        Execute the action in BOTH environments simultaneously.
        Same action applied to both trajectories from step 2 onwards.
        Return combined observation showing both trajectory states.
        Terminated when BOTH trajectories have reached max_steps.
        """

    def state(self) -> dict:
        """
        Returns state showing both trajectories:
        {
          "trajectory_a": { current_script, reward_components, debate_history, ... },
          "trajectory_b": { current_script, reward_components, debate_history, ... },
          "delta": trajectory_a.cumulative_reward - trajectory_b.cumulative_reward,
          "leading_trajectory": "A" or "B",
          "step_num": current step,
          "episode_id": ...
        }
        """

    def reward(self) -> float:
        """
        Called at episode end.
        Returns the contrastive reward — see ContrastiveReward below.
        """
```

---

## Step 3 — `rewards/contrastive_reward.py`

```python
class ContrastiveReward:
    """
    Computes a reward based on the delta between two parallel trajectories.

    The key insight: the Arbitrator is rewarded not just for doing well,
    but for doing BETTER than the counterfactual alternative.

    Reward formula:
    - delta = traj_a.cumulative_reward - traj_b.cumulative_reward
    - base_reward = max(traj_a.cumulative_reward, traj_b.cumulative_reward)
      (reward the better trajectory's absolute performance)
    - contrast_bonus = tanh(delta * 3) * 0.2
      (add up to +0.2 bonus when one trajectory clearly dominates)
    - final = base_reward + contrast_bonus, clipped to [0, 1]

    When delta is near zero (both trajectories performed similarly),
    contrast_bonus approaches 0 — the Arbitrator gets no extra credit
    for a choice that didn't matter. This encourages it to develop
    genuine preferences, not coin-flip decisions.

    When delta is large (one trajectory clearly won), contrast_bonus
    is maximised — this is the signal that matters most for learning
    action ordering.
    """

    def compute(
        self,
        traj_a: Trajectory,
        traj_b: Trajectory,
    ) -> ContrastiveRewardResult:
        # Returns ContrastiveRewardResult with:
        # final_reward, base_reward, contrast_bonus, delta,
        # winning_trajectory ("A" | "B" | "tie"),
        # winning_trajectory_type (e.g. "critic_first" | "defender_first")
```

---

## Step 4 — Update `training/rollout_function.py`

Add an AB-mode rollout function alongside the existing one:

```python
def build_ab_rollout_fn(ab_env: ABScriptEnv, max_steps: int = 5):
    """
    Rollout function for the A/B environment.

    The prompt format must now include both trajectory states:

    <|user|>
    TRAJECTORY A (Critic-first approach):
    Current script: {traj_a.current_script}
    Rewards so far: R1={r1_a} R2={r2_a} ... Total={total_a}

    TRAJECTORY B (Defender-first approach):
    Current script: {traj_b.current_script}
    Rewards so far: R1={r1_b} R2={r2_b} ... Total={total_b}

    Delta (A - B): {delta:.3f}

    Choose your next action (applied to BOTH trajectories):
    ...
    <|end|>
    """
```

---

## Step 5 — `scripts/run_ab_episode.py`

Demo and test script for the A/B environment:

```
python scripts/run_ab_episode.py --script S08 --steps 4 --verbose
```

Output format — show both trajectories side by side:

```
══ STEP 1 (FORCED) ══════════════════════════════════════════════════
TRAJECTORY A (Critic-first)                TRAJECTORY B (Defender-first)
Action: hook_rewrite                       Action: cta_placement
R1: 0.45 → 0.82 (+0.37)                   R1: 0.45 → 0.47 (+0.02)
R3: 0.71 → 0.54 (-0.17) ⚠ cultural drop   R3: 0.71 → 0.70 (-0.01)
Total: 0.58                                Total: 0.51

══ STEP 2 (FREE CHOICE) ══════════════════════════════════════════════
[Arbitrator sees both states and chooses...]

══ EPISODE END ═══════════════════════════════════════════════════════
Trajectory A final: 0.63
Trajectory B final: 0.71
Winner: B (defender-first was better for this script)
Delta: -0.08
Contrastive reward: 0.73
Lesson: On scripts with strong cultural voice, preserve the Defender's concern first.
```

---

## Step 6 — Update `demo/run_demo.py`

Add a `--ab-mode` flag:

```
python demo/run_demo.py --script S08 --ab-mode
```

In AB mode, Act 4 becomes "Two Paths" — show both trajectories playing out in parallel with their cumulative rewards, then the contrastive reward at the end. This is the most visually compelling part of the demo for technical judges.

---

## Step 7 — `tests/test_phase10.py`

- `ABScriptEnv.reset()` creates two environments with identical starting state
- Forced step 1 actions are correct: Trajectory A targets highest-severity claim, Trajectory B targets Defender's concern
- `ABScriptEnv.step()` applies same action to both trajectories
- `ContrastiveReward.compute()` returns correct delta and winning trajectory
- `contrast_bonus` approaches 0 when delta is near 0 (test with delta=0.01)
- `contrast_bonus` is positive when delta is large (test with delta=0.3)
- `final_reward` is always clipped to [0, 1]
- `state()` returns both trajectory states with correct delta

---

## Gate check

Run:
```
python scripts/run_ab_episode.py --script S08 --steps 4 --verbose
```

Must:
1. Show both trajectories running in parallel with different step-1 actions
2. Show non-zero delta at episode end (the two trajectories must diverge)
3. Show contrastive reward computed correctly
4. Print:
   ```
   PHASE 10 GATE: PASS — A/B environment running. Contrastive reward active. Delta: {delta:.3f}.
   ```