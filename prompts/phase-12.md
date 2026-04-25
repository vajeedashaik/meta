# Phase 12 — Retention Curve Simulator
> Paste this entire prompt into a fresh Claude Code session. Phase 11 must be complete before starting.

---

Phase 11 is complete. Longitudinal memory is active. Now build the Retention Curve Simulator — the most technically ambitious reward signal in the entire project. Instead of a binary viral/flopped predictor, this phase predicts a full second-by-second viewer drop-off curve for each script and rewards the Arbitrator for smoothing it.

**Why this is different from everything else:** Every other reward in this system scores a property of the script text. This one simulates *viewer behaviour over time*. It rewards the Arbitrator not for writing well, but for understanding that viewers are leaving at specific moments — and making targeted fixes that keep them watching longer.

**What makes it technically novel:** Most RL systems optimise a single scalar reward. This one optimises a curve — a sequence of predicted retention values at each second of the video. That is a fundamentally different and more expressive reward structure. The Arbitrator must learn that a fix which improves the hook (second 0–3) might hurt mid-video retention (second 15–30) if it removes something compelling from the body.

**Data source:** Public data exists for this. YouTube creator analytics exports on Reddit, viral vs flopped Reels transcripts with engagement data on Twitter/X, and academic datasets on short-video retention (TikTok Research API data published in papers). Use these to train the predictor.

---

## New files to create

```
viral_script_engine/
├── retention/
│   ├── __init__.py
│   ├── curve_predictor.py        # NEW — predicts second-by-second retention
│   ├── curve_scorer.py           # NEW — scores improvement between two curves
│   ├── feature_extractor.py      # NEW — extracts script features for prediction
│   └── training_data/
│       ├── build_dataset.py      # NEW — builds training data from public sources
│       └── retention_dataset.json  # NEW — populated by build_dataset.py
├── rewards/
│   └── r10_retention_curve.py    # NEW
└── tests/
    └── test_phase12.py           # NEW
```

---

## Step 1 — `retention/feature_extractor.py`

Extracts numerical features from a script that predict viewer retention. Zero LLM calls — purely structural analysis.

```python
class ScriptFeatures(BaseModel):
    # Hook features (predicts early drop-off 0–5s)
    hook_word_count: int
    hook_has_number: bool
    hook_has_question: bool
    hook_has_promise: bool
    hook_filler_score: float        # 0=no filler, 1=all filler (from R1 checks)

    # Pacing features (predicts mid-video retention 5–30s)
    avg_words_per_sentence: float
    sentence_count: int
    short_sentence_ratio: float     # sentences < 8 words / total sentences
    section_balance_score: float    # how evenly distributed hook:body:cta is

    # Content features (predicts late retention 30s+)
    specificity_score: float        # ratio of specific nouns/numbers to total words
    cultural_ref_count: int         # from R3 knowledge base
    cta_position_ratio: float       # position of CTA as fraction of total script

    # Platform fit features
    platform: str
    word_count: int
    length_vs_optimal: float        # word_count / optimal_script_length for platform

    def to_vector(self) -> List[float]:
        # Returns a flat numeric vector for model input
        # All booleans as 0/1, all floats as-is, platform as one-hot encoding
```

```python
class FeatureExtractor:
    def __init__(self):
        self.platform_registry = PlatformRegistry()
        self.cultural_kb = CulturalAlignmentReward()   # reuse existing knowledge base

    def extract(self, script: str, platform: str, region: str) -> ScriptFeatures:
        pass
```

---

## Step 2 — `retention/training_data/build_dataset.py`

Build the training dataset for the retention curve predictor.

```python
"""
Builds retention_dataset.json from publicly available data.

Data sources to use (all public, no scraping required):
1. Synthetic generation: use the Anthropic/Groq API to generate (script, retention_curve) pairs
   with diverse quality levels — good scripts get high curves, bad scripts get steep drops
2. Rule-based simulation: scripts with R1=0 get steep drop at second 3;
   scripts with R1=1 and R3=0.9 get gradual decline — encode known relationships

The dataset format:
{
  "samples": [
    {
      "script_id": "train_001",
      "script_text": "...",
      "platform": "Reels",
      "region": "Mumbai Gen Z",
      "retention_curve": [1.0, 0.95, 0.88, 0.72, 0.65, 0.60, ...],  // one value per 3 seconds
      "curve_source": "synthetic" | "rule_based",
      "quality_tier": "high" | "medium" | "low"
    }
  ]
}
"""
```

**Generate at minimum:**
- 50 high-quality scripts (retention stays above 0.7 throughout)
- 50 medium-quality scripts (retention drops to 0.4–0.7 mid-video)
- 50 low-quality scripts (steep drop to below 0.3 by second 10)

Retention curve generation rules (for rule-based samples):
- Second 0: always 1.0
- Second 3: `1.0 - (0.4 * (1 - r1_score))` — hook quality predicts early drop
- Second 10: `prev - (0.1 * (1 - r2_score))` — coherence predicts mid-video retention
- Second 20: `prev - (0.15 * (1 - r3_score))` — cultural alignment predicts late retention
- Final second: `prev - 0.05` — natural decay always present

---

## Step 3 — `retention/curve_predictor.py`

A lightweight ML model that predicts a 10-point retention curve from script features.

```python
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor
import joblib

class RetentionCurvePredictor:
    """
    Predicts a 10-point retention curve from script features.
    10 points = retention at seconds [0, 3, 6, 10, 15, 20, 25, 30, 45, 60].

    Uses a scikit-learn MultiOutputRegressor wrapping GradientBoostingRegressor.
    Lightweight enough to run on CPU without GPU.
    Trained once on retention_dataset.json, saved to retention/model.joblib.

    Why not a neural network: this predictor needs to run on every step() call
    during training. A sklearn model runs in <1ms. A neural network would
    slow the environment loop unacceptably.
    """

    MODEL_PATH = "retention/model.joblib"
    CURVE_TIMEPOINTS = [0, 3, 6, 10, 15, 20, 25, 30, 45, 60]   # seconds

    def __init__(self):
        if os.path.exists(self.MODEL_PATH):
            self.model = joblib.load(self.MODEL_PATH)
            self._trained = True
        else:
            self.model = MultiOutputRegressor(
                GradientBoostingRegressor(n_estimators=100, max_depth=4, random_state=42)
            )
            self._trained = False

    def train(self, dataset_path: str = "retention/training_data/retention_dataset.json"):
        """
        Train the predictor on the retention dataset.
        Saves model to MODEL_PATH after training.
        Prints train/val MAE for each timepoint.
        """

    def predict(self, features: ScriptFeatures) -> RetentionCurve:
        """
        Returns RetentionCurve with:
        - timepoints: List[int] — the 10 timepoints in seconds
        - values: List[float] — predicted retention at each timepoint (0–1)
        - area_under_curve: float — integral approximation (higher = better overall retention)
        - drop_off_point: int — first timepoint where retention drops below 0.5
        """
        if not self._trained:
            raise RuntimeError("Model not trained. Run train() first.")
        vector = features.to_vector()
        predictions = self.model.predict([vector])[0]
        # Clip to [0, 1] and enforce monotonic decrease (retention can't go up)
        values = self._enforce_monotonic_decrease(np.clip(predictions, 0, 1))
        return RetentionCurve(timepoints=self.CURVE_TIMEPOINTS, values=values.tolist())
```

---

## Step 4 — `retention/curve_scorer.py`

```python
class RetentionCurveScorer:
    """
    Scores the improvement between two retention curves.

    The reward is not just "did the curve improve overall" but
    "which specific parts of the curve improved, and by how much?"

    This gives the Arbitrator credit for targeted improvements:
    - hook fix → reward for improvement at seconds 0–6
    - body fix → reward for improvement at seconds 10–30
    - CTA fix → reward for improvement at seconds 45–60
    """

    # Which action types should improve which parts of the curve
    ACTION_CURVE_MAP = {
        "hook_rewrite":     [0, 3, 6],          # early timepoints
        "section_reorder":  [10, 15, 20],        # mid timepoints
        "cultural_ref_sub": [15, 20, 25, 30],    # mid-to-late
        "cta_placement":    [45, 60],            # late timepoints
    }

    def score(
        self,
        original_curve: RetentionCurve,
        new_curve: RetentionCurve,
        action_type: str,
    ) -> CurveScorerResult:
        """
        1. Compute overall AUC improvement: (new_auc - original_auc) / original_auc
        2. Compute targeted improvement: avg improvement at timepoints relevant to action_type
        3. Compute regression penalty: any timepoint that got WORSE gets penalised

        final_score = 0.5 * overall_improvement
                    + 0.35 * targeted_improvement
                    - 0.15 * regression_penalty
        clipped to [0, 1]

        Returns CurveScorerResult with: final_score, overall_improvement,
        targeted_improvement, regression_penalty, improved_timepoints, worsened_timepoints
        """
```

---

## Step 5 — `rewards/r10_retention_curve.py`

```python
class RetentionCurveReward:
    """
    Wraps the full retention prediction + scoring pipeline into a reward signal.
    """

    def __init__(self):
        self.extractor = FeatureExtractor()
        self.predictor = RetentionCurvePredictor()
        self.scorer = RetentionCurveScorer()
        self._original_curve_cache = {}   # cache by episode_id to avoid re-computing

    def score(
        self,
        original_script: str,
        rewritten_script: str,
        platform: str,
        region: str,
        action_type: str,
        episode_id: str,
    ) -> RetentionRewardResult:
        # 1. Cache original curve (compute only once per episode)
        if episode_id not in self._original_curve_cache:
            orig_features = self.extractor.extract(original_script, platform, region)
            self._original_curve_cache[episode_id] = self.predictor.predict(orig_features)

        # 2. Predict curve for rewritten script
        new_features = self.extractor.extract(rewritten_script, platform, region)
        new_curve = self.predictor.predict(new_features)

        # 3. Score the improvement
        result = self.scorer.score(
            original_curve=self._original_curve_cache[episode_id],
            new_curve=new_curve,
            action_type=action_type,
        )

        return RetentionRewardResult(
            score=result.final_score,
            original_curve=self._original_curve_cache[episode_id],
            new_curve=new_curve,
            curve_delta=result,
        )
```

---

## Step 6 — Update `environment/env.py`

In `__init__()`:
```python
self.r10 = RetentionCurveReward()
```

In `step()`, after Rewriter executes:
```python
components.r10_retention_curve = self.r10.score(
    original_script=self._original_script,
    rewritten_script=new_script,
    platform=self._current_platform,
    region=self._current_region,
    action_type=action.action_type,
    episode_id=self._episode_id,
).score
```

Update `RewardComponents`:
```python
r10_retention_curve: Optional[float] = None
```

Update `RewardAggregator` weights (10 rewards + process):
```python
WEIGHTS = {
    "r1": 0.12, "r2": 0.10, "r3": 0.10,
    "r4": 0.10, "r5": 0.08, "r6": 0.07,
    "r7": 0.07, "r8": 0.08, "r9": 0.08,
    "r10": 0.10, "process": 0.10,
}
```

---

## Step 7 — Update `demo/run_demo.py`

In Act 5 (The Rewrite + Reward), add a retention curve visualisation using ASCII art:

```
PREDICTED RETENTION CURVE:

Before rewrite:
  100% |████████
   75% |        ████
   50% |            ████
   25% |                ████████
    0% +--+--+--+--+--+--+--+--+--+
       0s 3s 6s 10 15 20 25 30 45 60s

After rewrite:
  100% |████████████
   75% |            ████████
   50% |                    ████
   25% |                        ████
    0% +--+--+--+--+--+--+--+--+--+
       0s 3s 6s 10 15 20 25 30 45 60s

Improvement: AUC 0.41 → 0.62 (+51%)
Drop-off point: 6s → 20s (viewers staying 3× longer before leaving)
```

---

## Step 8 — `scripts/train_retention_model.py`

One-time training script:
```
python scripts/train_retention_model.py
```

1. Calls `build_dataset.py` to generate `retention_dataset.json` if it doesn't exist
2. Trains the `RetentionCurvePredictor`
3. Prints train/val MAE per timepoint
4. Saves model to `retention/model.joblib`
5. Prints: "Retention model trained. Avg MAE: X.XX. Model saved."

---

## Step 9 — `tests/test_phase12.py`

- `FeatureExtractor.extract()` produces correct feature vector for a known script
- `FeatureExtractor.to_vector()` returns a flat numeric list with no NaN values
- `RetentionCurvePredictor.predict()` raises RuntimeError if model not trained
- Predicted curve is monotonically non-increasing (retention can't go up)
- Predicted curve values are all in [0, 1]
- `RetentionCurveScorer.score()` correctly rewards targeted improvement at action-relevant timepoints
- `RetentionCurveScorer.score()` applies regression penalty when any timepoint worsens
- `RetentionCurveReward` uses cached original curve (test that extractor is called only once per episode)
- `env.step()` includes r10 in reward components

---

## Gate check

First train the model:
```
python scripts/train_retention_model.py
```

Then run:
```
python scripts/run_dummy_episode.py --difficulty easy --steps 3 --verbose
```

Must:
1. Show R10 (retention curve) in reward components
2. Show before/after curve in episode log
3. Show AUC improvement
4. Print:
   ```
   PHASE 12 GATE: PASS — Retention curve predictor active. R10 firing. AUC improvement: +X.XX.
   ```