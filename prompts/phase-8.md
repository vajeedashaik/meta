# Phase 8 — Creator Persona Modelling
> Paste this entire prompt into a fresh Claude Code session. Phase 7 must be complete before starting.

---

Phase 7 is complete. Process rewards are active. Now add Creator Persona Modelling — the single strongest argument for Meta deployment. The Arbitrator learns to give contextually appropriate advice based on who the creator is, not just what the script says.

**The core insight:** A beginner creator with 200 followers and a verified creator with 500k need completely different fixes. The same hook problem means different things at different stages. Right now the environment treats all creators identically. This phase changes that.

**Why Meta would deploy this:** Meta already has all this data per creator — follower count, posting frequency, engagement rate, niche maturity. They could slot the Creator Profile directly into the observation space and have a personalised coach at scale for 80M+ creators instantly. No retraining needed — just replace the simulated profiles with real data.

---

## New files to create

```
viral_script_engine/
├── personas/
│   ├── __init__.py
│   ├── creator_profile.py        # NEW — profile schema and tier logic
│   ├── persona_kb.py             # NEW — advice rules per tier
│   └── profile_generator.py     # NEW — generates synthetic profiles for training
├── rewards/
│   └── r8_persona_fit.py         # NEW
├── data/
│   └── persona_advice_kb.json    # NEW — tier-specific advice rules
└── tests/
    └── test_phase8.py            # NEW
```

---

## Step 1 — `personas/creator_profile.py`

```python
from enum import Enum
from pydantic import BaseModel
from typing import List, Optional

class CreatorTier(str, Enum):
    BEGINNER = "beginner"           # 0–1k followers
    GROWING = "growing"             # 1k–10k followers
    ESTABLISHED = "established"     # 10k–100k followers
    VERIFIED = "verified"           # 100k+ followers

class PostingFrequency(str, Enum):
    RARE = "rare"           # < 1 post/week
    REGULAR = "regular"     # 1–3 posts/week
    FREQUENT = "frequent"   # 4–7 posts/week
    DAILY = "daily"         # 1+ posts/day

class CreatorProfile(BaseModel):
    creator_id: str
    tier: CreatorTier
    follower_count: int
    posting_frequency: PostingFrequency
    niche: str                          # e.g. "personal finance", "cooking", "tech"
    niche_maturity: str                 # "new_to_niche" | "established_in_niche" | "niche_authority"
    avg_engagement_rate: float          # 0.0–1.0 (likes+comments / followers)
    avg_retention_rate: float           # 0.0–1.0 (estimated average watch-through)
    past_weak_points: List[str]         # critique classes they repeatedly struggle with
    past_strong_points: List[str]       # critique classes they consistently handle well
    voice_descriptors: List[str]        # e.g. ["direct", "humorous", "educational", "regional"]
    platform_primary: str               # "Reels" | "Shorts" | "TikTok"

    @property
    def needs_fundamentals(self) -> bool:
        # True for beginner and growing tiers — focus on hook and CTA basics
        return self.tier in [CreatorTier.BEGINNER, CreatorTier.GROWING]

    @property
    def needs_refinement(self) -> bool:
        # True for established and verified — focus on cultural alignment and originality
        return self.tier in [CreatorTier.ESTABLISHED, CreatorTier.VERIFIED]
```

---

## Step 2 — `data/persona_advice_kb.json`

Rules that define what advice is appropriate per creator tier. The Arbitrator's decisions will be evaluated against these rules by R8.

```json
{
  "beginner": {
    "priority_actions": ["hook_rewrite", "cta_placement"],
    "deprioritised_actions": ["cultural_ref_sub", "section_reorder"],
    "rationale": "Beginners need fundamentals first. Hook and CTA drive the most growth at low follower counts. Cultural refinement is premature when basic structure is broken.",
    "max_changes_per_episode": 2,
    "forbidden_advice": ["optimise for saves", "target niche algorithm signals"]
  },
  "growing": {
    "priority_actions": ["hook_rewrite", "section_reorder"],
    "deprioritised_actions": ["cultural_ref_sub"],
    "rationale": "Growing creators have hooks working partially. Focus on pacing and structure to push past the 10k ceiling.",
    "max_changes_per_episode": 3,
    "forbidden_advice": []
  },
  "established": {
    "priority_actions": ["cultural_ref_sub", "section_reorder", "cta_placement"],
    "deprioritised_actions": [],
    "rationale": "Established creators have basics down. Cultural specificity and originality drive differentiation at this tier.",
    "max_changes_per_episode": 4,
    "forbidden_advice": ["simplify the hook"]
  },
  "verified": {
    "priority_actions": ["cultural_ref_sub", "section_reorder"],
    "deprioritised_actions": ["hook_rewrite"],
    "rationale": "Verified creators have a proven hook style. Do not touch it. Focus on deeper content quality and cultural resonance.",
    "max_changes_per_episode": 5,
    "forbidden_advice": ["change the hook", "add a CTA"]
  }
}
```

---

## Step 3 — `rewards/r8_persona_fit.py`

```python
class PersonaFitReward:
    """
    Measures whether the Arbitrator's chosen action is appropriate
    for the creator's tier and profile.

    Scoring:
    - Action is in priority_actions for this tier:      1.0
    - Action is neutral (not in priority OR deprioritised): 0.5
    - Action is in deprioritised_actions for this tier: 0.2
    - Action is explicitly forbidden for this tier:     0.0

    Additionally, if past_weak_points contains the critique_class being
    addressed, add +0.1 bonus (the Arbitrator correctly targeting a known
    recurring issue). Cap total at 1.0.
    """

    def __init__(self, kb_path: str = "data/persona_advice_kb.json"):
        pass

    def score(
        self,
        action: ArbitratorAction,
        creator_profile: CreatorProfile,
        addressed_critique_class: str,
    ) -> PersonaFitResult:
        # Returns PersonaFitResult with: score, tier_match, is_forbidden,
        # recurring_weakness_bonus, explanation
```

---

## Step 4 — `personas/profile_generator.py`

Generates synthetic Creator Profiles for training. Each curriculum episode config will have an associated profile.

```python
class ProfileGenerator:
    """
    Generates realistic Creator Profiles for training episodes.
    Profiles are deterministic given a seed — same seed = same profile.
    """

    NICHES = [
        "personal finance", "cooking", "fitness", "tech reviews",
        "small business", "agriculture", "fashion", "comedy",
        "productivity", "travel", "education", "local culture"
    ]

    def generate(self, tier: CreatorTier, niche: str, seed: int = 42) -> CreatorProfile:
        """
        Generate a realistic profile for a given tier and niche.

        Follower counts should be realistic for the tier:
        - beginner: 50–999
        - growing: 1000–9999
        - established: 10000–99999
        - verified: 100000–2000000

        Engagement rates should decrease as follower count increases
        (this is real platform behaviour):
        - beginner: 0.08–0.15
        - growing: 0.04–0.08
        - established: 0.02–0.04
        - verified: 0.01–0.02

        past_weak_points: randomly sample 1–3 critique classes
        past_strong_points: randomly sample 1–2 critique classes (different from weak)
        """

    def generate_batch(self, n: int, tier_distribution: dict = None) -> List[CreatorProfile]:
        """
        Generate n profiles with realistic tier distribution.
        Default distribution: beginner=40%, growing=35%, established=20%, verified=5%
        (mirrors real platform demographics)
        """
```

---

## Step 5 — Update `environment/observations.py`

Add `CreatorProfile` to `Observation`:

```python
class Observation(BaseModel):
    # ... existing fields ...
    creator_profile: Optional[CreatorProfile] = None   # NEW
```

The Arbitrator now sees the creator's tier, recurring weak points, and voice descriptors before making its decision. Update the prompt template in `training/rollout_function.py` to include:

```
CREATOR PROFILE:
Tier: {tier} ({follower_count} followers)
Posting frequency: {posting_frequency}
Recurring weak points: {past_weak_points}
Voice: {voice_descriptors}
Niche maturity: {niche_maturity}
```

---

## Step 6 — Update `environment/env.py`

In `__init__()`:
```python
self.profile_generator = ProfileGenerator()
self.r8 = PersonaFitReward()
```

In `reset()`:
1. Generate or load a `CreatorProfile` for this episode
2. Profile tier should match the episode's difficulty:
   - easy episodes → beginner/growing profiles (simpler advice needed)
   - medium episodes → growing/established profiles
   - hard episodes → established/verified profiles (more nuanced advice required)
3. Store profile in episode state and include in observation

In `step()`, after computing R1–R7, add:
```python
components.r8_persona_fit = self.r8.score(
    action=action,
    creator_profile=self._current_profile,
    addressed_critique_class=addressed_claim.critique_class,
).score
```

Update `RewardComponents`:
```python
r8_persona_fit: Optional[float] = None
```

Update `RewardAggregator` weights:
```python
WEIGHTS = {
    "r1": 0.18,
    "r2": 0.13,
    "r3": 0.13,
    "r4": 0.13,
    "r5": 0.13,
    "r6": 0.08,
    "r7": 0.08,
    "r8": 0.10,
    "process": 0.10,
}
```

---

## Step 7 — Update `data/curriculum/` JSONL files

Add `creator_profile` to each episode config. For each existing config, generate a profile matching the difficulty tier using `ProfileGenerator`. Re-save all three JSONL files with the profile included.

---

## Step 8 — Update `demo/run_demo.py`

In Act 1 (The Raw Script), show the Creator Profile as a side panel:

```
╔══ CREATOR PROFILE ═════════════════════╗
│ Tier:        Growing (4,200 followers) │
│ Frequency:   Regular (3×/week)         │
│ Niche:       Personal finance          │
│ Weak points: hook_weakness, cta_buried │
│ Voice:       direct, Hinglish, relatable│
╚════════════════════════════════════════╝
```

In Act 4 (The Arbitrator Decides), show whether the action was persona-appropriate:

```
Persona fit: ✓ hook_rewrite is priority action for growing tier
```

---

## Step 9 — `tests/test_phase8.py`

- `ProfileGenerator.generate()` produces valid profiles within realistic ranges per tier
- `ProfileGenerator.generate_batch()` matches the expected tier distribution
- `PersonaFitReward` scores 1.0 for a priority action matching the creator's tier
- `PersonaFitReward` scores 0.0 for a forbidden action
- `PersonaFitReward` applies the +0.1 recurring weakness bonus correctly
- `env.reset()` assigns a profile consistent with the episode difficulty
- Profile appears in observation dict
- Prompt template includes creator profile fields

---

## Meta deployment note — include this in README

Add a section to `README.md` under "Why This Matters for Meta":

```markdown
### Creator Persona Modelling — Ready for Production

The Creator Profile in the observation space uses only data Meta already has:
follower count, posting frequency, engagement rate, niche. To deploy this
system at scale, Meta would replace the simulated profiles with real creator
data from their internal systems. No retraining needed — the Arbitrator
already knows how to use profile data because it trained on it.

This turns the Viral Script Debugging Engine from a generic script coach
into a personalised creative collaborator for 80M+ creators, each receiving
advice calibrated to exactly where they are in their growth journey.
```

---

## Gate check

Run:
```
python scripts/run_dummy_episode.py --difficulty medium --steps 3 --verbose
```

Must:
1. Show creator profile in episode log
2. Show R8 (persona fit) in reward components
3. Show profile in observation dict
4. Print:
   ```
   PHASE 8 GATE: PASS — Creator persona active. R8 (persona fit) firing. Profile tier: {tier}.
   ```