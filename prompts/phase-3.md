# Phase 3 — Curriculum Dataset + GRPO Training
> Paste this entire prompt into a fresh Claude Code session. Phases 0–2 must be complete, baseline curves saved, before starting.

---

Phases 0–2 are complete. The environment has all 5 rewards, anti-gaming protections are live, and baseline reward curves are saved in `logs/baseline_reward_curves.png`. Now build the curriculum datasets and the GRPO training pipeline.

**The training script must connect to the live OpenEnv environment — not a static dataset.**

---

## Step 1 — `data/curriculum/build_curriculum.py`

Build three curriculum tiers. Each is a JSONL file where each line is one episode config.

**Episode config schema:**
```json
{
  "episode_config_id": "easy_001",
  "difficulty": "easy",
  "script_id": "S01",
  "script_text": "...",
  "region": "Mumbai Gen Z",
  "platform": "Reels",
  "niche": "personal finance",
  "dominant_flaw": "buried_hook",
  "expected_critique_class": "hook_weakness",
  "expected_action": "hook_rewrite",
  "curriculum_notes": "One obvious flaw. Critic should win immediately. Strong reward signal on step 1."
}
```

**Generate:**
- `data/curriculum/easy_tier.jsonl` — 20 configs (10 from existing scripts + 10 synthetic)
- `data/curriculum/medium_tier.jsonl` — 15 configs (trade-off scenarios where Critic and Defender both have valid points)
- `data/curriculum/hard_tier.jsonl` — 10 configs (fixing the top critique damages R3 — explicit conflicts)

**For synthetic scripts**, create `data/curriculum/generate_synthetic_scripts.py`:

Use the Anthropic API with this prompt pattern:
```
Generate a realistic 60-90 second Reels script for [niche] targeting [region].
Intentionally include [flaw_type] as the dominant flaw.
The flaw should be [easy|medium|hard] to diagnose.
```

Generate: 10 easy, 5 medium, 5 hard synthetic scripts. Save to `data/curriculum/synthetic_scripts.json`.

---

## Step 2 — `training/rollout_function.py`

This bridges TRL's `GRPOTrainer` to the live OpenEnv environment. It's the most critical file in this phase.

```python
def build_rollout_fn(env: ViralScriptEnv, max_steps: int = 5):
    """
    Returns a function compatible with TRL's GRPOTrainer rollout interface.
    
    For each prompt in the batch:
    1. Parse the episode config embedded in prompt metadata
    2. Reset the env with that config
    3. Run the model to generate an action (JSON)
    4. Execute the action in the env
    5. Collect the final episode reward
    
    Returns: (completions: List[str], rewards: List[float])
    """

    def rollout_fn(prompts: List[str], model, tokenizer) -> Tuple[List[str], List[float]]:
        ...

    return rollout_fn
```

**Prompt format for the Arbitrator model:**
```
<|system|>
You are an expert content strategist acting as an Arbitrator in a script improvement debate.
You observe a debate between a Critic and Defender about a creator's script.
You must choose exactly ONE action to improve the script.

AVAILABLE ACTIONS: hook_rewrite | section_reorder | cultural_ref_sub | cta_placement

OUTPUT FORMAT (JSON only):
{"action_type": "...", "target_section": "...", "instruction": "...", "critique_claim_id": "...", "reasoning": "..."}
<|end|>

<|user|>
CURRENT SCRIPT:
{current_script}

REGION: {region} | PLATFORM: {platform} | NICHE: {niche}

CRITIC CLAIMS:
{formatted_critic_claims}

DEFENDER RESPONSE:
Core strength: {core_strength}
Defense: {defense_argument}
Flagged claims: {flagged_claims}

CURRENT REWARDS: R1={r1:.2f} R2={r2:.2f} R3={r3} R4={r4} R5={r5}
STEP: {step_num}/{max_steps}

Choose your action:
<|end|>
```

---

## Step 3 — `training/train_grpo.py`

Make this runnable as both a local script and a Colab notebook cell.

```python
"""
GRPO Training — Viral Script Debugging Engine
TRL + Unsloth for memory-efficient training.

Local dry-run:    python training/train_grpo.py --dry-run
Full training:    python training/train_grpo.py --tier easy,medium --steps 200
"""

from unsloth import FastLanguageModel
from trl import GRPOTrainer, GRPOConfig

def load_model(model_name: str, max_seq_length: int = 2048):
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        dtype=None,          # auto-detect
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )
    return model, tokenizer

def build_grpo_config(output_dir, num_steps, dry_run) -> GRPOConfig:
    return GRPOConfig(
        output_dir=output_dir,
        num_train_epochs=1,
        max_steps=5 if dry_run else num_steps,
        per_device_train_batch_size=1 if dry_run else 4,
        num_generations=4 if dry_run else 8,
        gradient_accumulation_steps=4,
        learning_rate=5e-6,
        max_grad_norm=0.1,
        warmup_ratio=0.1,
        logging_steps=1,
        save_steps=50,
        report_to="wandb" if os.getenv("WANDB_API_KEY") else "none",
        use_vllm=False,
        temperature=0.8,
        top_p=0.9,
        max_new_tokens=256,
    )
```

**Model saving — CRITICAL:**
```python
# Use save_pretrained_merged — NOT naive upcast from 4-bit
model.save_pretrained_merged(
    f"{output_dir}/final_model",
    tokenizer,
    save_method="merged_16bit",
)
```

**CLI flags:**
- `--tier` — comma-separated tiers: `easy`, `medium`, `hard`
- `--steps` — number of training steps (default: 200)
- `--dry-run` — run 5 steps with batch_size=1 to validate pipeline
- `--model` — base model (default: `unsloth/Qwen2.5-7B-Instruct-bnb-4bit`)
- `--output-dir` — checkpoint directory (default: `outputs/checkpoints/`)
- `--wandb` — enable WandB logging

---

## Step 4 — `training/reward_curves.py`

```python
def plot_training_curves(
    baseline_log_path: str = "logs/baseline_results.json",
    training_log_path: str = "logs/training_results.json",
    output_path: str = "logs/training_vs_baseline.png",
):
    """
    Judge-facing comparison plot.
    Layout: 2 rows × 3 cols (R1, R2, R3, R4, R5, Total)
    
    Per subplot:
    - Grey line: baseline reward per episode
    - Blue line: trained reward per episode
    - Horizontal dashed line: baseline mean
    - Both axes labelled
    
    Figure title: "Trained vs Untrained Arbitrator — Reward Improvement"
    Save PNG dpi=150. Also save PDF for README.
    
    Print improvement summary:
      R1: baseline=X.XX → trained=Y.YY (+Z.ZZ)
      ...
    """
```

---

## Step 5 — `training/eval_trained_model.py`

After training: run 20 evaluation episodes with the trained model. Use the same 20 episode configs as the baseline run for a fair comparison. Save to `logs/trained_results.json`. Then call `plot_training_curves()`.

---

## Step 6 — `tests/test_training_pipeline.py`

- `build_training_prompts("easy")` returns non-empty dataset with correct prompt format
- `rollout_fn` completes one episode given a mock model returning random valid JSON
- `GRPOConfig` builds without error
- Model saving path uses `save_pretrained_merged`, not `save_pretrained`
- `plot_training_curves` generates a PNG file given valid JSON inputs

---

## Gate check

Run:
```
python training/train_grpo.py --dry-run
```

Must:
1. Complete 5 training steps without error
2. Print reward values for each step
3. Show training loop is connected to the live environment (not a static dataset)
4. Print:
   ```
   PHASE 3 GATE: PASS — Dry run complete. Training pipeline connected to live environment.
   ```

**The full training run happens onsite when compute credits are available. Do not attempt to run it now.**