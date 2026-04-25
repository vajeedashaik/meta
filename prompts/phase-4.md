# Phase 4 — Critic Escalation Engine (Theme 4: Self-Improvement)
> Paste this entire prompt into a fresh Claude Code session. Phases 0–3 must be complete and the training dry-run passing before starting.

---

Phases 0–3 are complete. The training pipeline is validated. Now build the self-improvement loop that satisfies Theme 4: a Critic Escalation Engine that generates harder critique challenges automatically as the Arbitrator improves.

This is what separates this submission from a standard RL environment. Every other team builds a fixed task. This environment gets harder as the agent gets better.

---

## Step 1 — `escalation/difficulty_tracker.py`

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json

@dataclass
class CritiqueClassRecord:
    critique_class: str
    total_episodes: int = 0
    resolved_episodes: int = 0       # episodes where R4 >= 0.8
    consecutive_resolutions: int = 0  # current streak
    mastery_threshold: int = 3        # consecutive resolutions needed for mastery
    is_mastered: bool = False
    avg_r4_score: float = 0.0
    last_10_r4_scores: List[float] = field(default_factory=list)

class DifficultyTracker:
    CRITIQUE_CLASSES = [
        "hook_weakness", "pacing_issue", "cultural_mismatch",
        "cta_buried", "coherence_break", "retention_risk"
    ]

    def __init__(self, persistence_path: str = "logs/difficulty_tracker.json"):
        # Init one CritiqueClassRecord per class
        # Load from persistence_path if it exists

    def record_episode(self, dominant_critique_class: str, r4_score: float, episode_id: str):
        """
        Update the record for the dominant critique class.
        Resolved = r4_score >= 0.8.
        Update consecutive_resolutions streak (reset to 0 on failure).
        Set is_mastered = True at consecutive_resolutions >= mastery_threshold.
        Save to disk after every update.
        """

    def get_next_difficulty_class(self) -> str:
        """
        Priority:
        1. If any class is mastered AND a harder version exists from the escalation engine → return it
        2. Else → class with lowest avg_r4_score that has had >= 3 episodes
        3. Fallback → "hook_weakness"
        """

    def get_mastered_classes(self) -> List[str]:
        return [k for k, v in self.records.items() if v.is_mastered]

    def get_hardest_unsolved_class(self) -> str:
        # Lowest avg_r4_score among non-mastered classes

    def summary(self) -> dict:
        # JSON-serialisable summary for logging and demo
```

---

## Step 2 — `escalation/critic_escalation_engine.py`

```python
@dataclass
class EscalatedChallenge:
    source_class: str           # which mastered class this escalates from
    script_text: str
    region: str
    platform: str
    dominant_flaw: str
    conflicting_flaw: str       # the flaw that makes fixing dominant_flaw harder
    why_its_harder: str         # one sentence
    optimal_action_order: List[str]
    trap_action: str            # the action that looks right but leads to worse total reward
    difficulty_level: str = "self_generated"
    generated_at: str = ""      # ISO timestamp

class CriticEscalationEngine:
    def __init__(self, model_name: str = "claude-sonnet-4-20250514"):
        self.escalated_classes: Dict[str, List[EscalatedChallenge]] = {}

    def escalate(
        self,
        mastered_class: str,
        original_script_example: str,
        region: str,
        platform: str,
    ) -> EscalatedChallenge:
        """
        System prompt:
        You are designing training challenges for an RL agent learning to improve video scripts.
        The agent has mastered detecting and fixing '{mastered_class}' flaws.

        Generate a harder challenge:
        1. Create a script with a '{mastered_class}' flaw that is MORE SUBTLE than the example
        2. Add a CONFLICTING CONSTRAINT: fixing the '{mastered_class}' flaw should create or
           worsen a different flaw from: {other_classes}
        3. Difficulty: HARD — agent must learn action ordering, not just action selection

        A challenge is good when: fixing the obvious flaw first leads to WORSE total reward
        than fixing a less obvious flaw first.

        Return JSON only:
        {
          "script_text": "...",
          "dominant_flaw": "...",
          "conflicting_flaw": "...",
          "why_its_harder": "one sentence",
          "optimal_action_order": ["action1", "action2"],
          "trap_action": "action that looks correct but degrades total reward"
        }
        """

    def get_next_challenge(self, difficulty_tracker: DifficultyTracker) -> Optional[EscalatedChallenge]:
        # Return next escalated challenge based on mastered classes
        # Return None if no classes are mastered yet
```

---

## Step 3 — Wire escalation into `environment/env.py`

**Update `__init__` signature:**
```python
def __init__(
    self,
    scripts_path: str = "data/test_scripts/scripts.json",
    max_steps: int = 5,
    difficulty: str = "easy",
    use_anti_gaming: bool = True,
    use_escalation: bool = True,
    difficulty_tracker: Optional[DifficultyTracker] = None,
    escalation_engine: Optional[CriticEscalationEngine] = None,
):
    # Create new DifficultyTracker / CriticEscalationEngine if not provided
```

**Update `reset()`:**
1. After existing reset logic, call `difficulty_tracker.get_mastered_classes()`
2. If any classes are mastered: call `escalation_engine.get_next_challenge(difficulty_tracker)`
3. If a challenge is returned: use the escalated script instead of the curriculum script
4. Set `observation.difficulty_level = "self_generated"`
5. Log that escalation was used (print + include in info dict)

**Update `step()`:**
After episode ends (terminated=True):
1. Determine `dominant_critique_class` = the critique_class with the most claims in the first Critic output of this episode
2. Call `difficulty_tracker.record_episode(dominant_critique_class, r4_score, episode_id)`

---

## Step 4 — `scripts/run_escalation_demo.py`

```
python scripts/run_escalation_demo.py --episodes 50 --verbose
python scripts/run_escalation_demo.py --episodes 10 --verbose   # for gate check
```

Behaviour:
1. Run N episodes with the trained model (from `outputs/checkpoints/final_model`)
2. After each episode: log `difficulty_tracker.summary()`
3. Print clearly when mastery is achieved for a class and when escalation first activates
4. At the end, print a "difficulty progression" report:
   - Which classes were mastered and at which episode
   - How many escalated challenges were generated
   - Whether escalated challenges produced lower R4 scores than the original class (proof escalation is working)

Save progression to `logs/escalation_progression.json`.

**Generate `logs/escalation_chart.png`:**
- X-axis: episode number, labelled
- Y-axis (left): difficulty score (1=easy, 2=medium, 3=hard, 4=self_generated)
- Y-axis (right): R4 score per episode
- Both overlaid on same plot
- Title: "Difficulty Progression — Self-Generated Curriculum"
- This chart is your Theme 4 story for judges

---

## Step 5 — `tests/test_escalation.py`

- `DifficultyTracker.record_episode()` correctly tracks consecutive resolutions
- Mastery triggers at exactly 3 consecutive resolutions, not 2
- Mastery resets if agent fails (r4 < 0.8) on a subsequent episode
- `CriticEscalationEngine.escalate()` returns valid `EscalatedChallenge` from mock LLM
- `env.reset()` uses escalated script when mastery is achieved (integration test with mocked escalation engine)
- Difficulty progression JSON is saved correctly

---

## Gate check

Run:
```
python scripts/run_escalation_demo.py --episodes 10 --verbose
```

Must:
1. Complete 10 episodes without error
2. Show `DifficultyTracker` updating after each episode
3. Print escalation stats at the end
4. Save `logs/escalation_chart.png`
5. Print:
   ```
   PHASE 4 GATE: PASS — Escalation engine operational. {n} classes mastered. {m} escalated challenges generated.
   ```