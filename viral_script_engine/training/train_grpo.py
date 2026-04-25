#!/usr/bin/env python3
"""
GRPO Training — Viral Script Debugging Engine
TRL + Unsloth for memory-efficient training.

Local dry-run:    python training/train_grpo.py --dry-run
Full training:    python training/train_grpo.py --tier easy,medium --steps 200

Colab usage:
  import subprocess
  subprocess.run(["python", "training/train_grpo.py", "--tier", "easy", "--steps", "200"])
"""
import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Model loading (unsloth — GPU only, skipped for dry-run)
# ---------------------------------------------------------------------------

def load_model(model_name: str, max_seq_length: int = 2048):
    try:
        from unsloth import FastLanguageModel
    except ImportError:
        raise RuntimeError(
            "unsloth is not installed. Install it on a CUDA machine: "
            "pip install unsloth"
        )

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        dtype=None,
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


def build_grpo_config(output_dir: str, num_steps: int, dry_run: bool):
    try:
        from trl import GRPOConfig
    except ImportError:
        raise RuntimeError("trl is not installed. Install it: pip install trl")

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


# ---------------------------------------------------------------------------
# Dry-run mode (no GPU required — validates pipeline connectivity)
# ---------------------------------------------------------------------------

class _DryRunModel:
    """Mock model for dry-run: returns a valid JSON action for any prompt."""

    def __call__(self, prompt: str) -> str:
        import random
        actions = ["hook_rewrite", "section_reorder", "cultural_ref_sub", "cta_placement"]
        return json.dumps({
            "action_type": random.choice(actions),
            "target_section": "hook",
            "instruction": "Dry-run mock instruction.",
            "critique_claim_id": "C1",
            "reasoning": "Dry-run mock reasoning.",
        })


def _patch_rewards_for_dry_run():
    """
    Patch R2 and R5 to avoid loading sentence_transformers during dry-run.
    On Windows with Application Control policies, pyarrow's DLL is blocked.
    Both rewards fall back to fixed scores sufficient for pipeline validation.
    """
    from viral_script_engine.rewards import r2_coherence, r5_defender_preservation

    class _MockR2Result:
        score = 0.75
        raw_similarity = 0.85
        interpretation = "good_coherence"

    class _MockR5Result:
        score = 0.70
        max_similarity = 0.80
        best_matching_sentence = "[dry-run mock]"

    def _mock_r2_score(self, original, rewritten):
        return _MockR2Result()

    def _mock_r5_score(self, defender_output, rewritten_script):
        return _MockR5Result()

    r2_coherence.CoherenceReward.score = _mock_r2_score
    r5_defender_preservation.DefenderPreservationReward.score = _mock_r5_score


def run_dry_run(tiers: list, steps: int, output_dir: str):
    _patch_rewards_for_dry_run()
    from viral_script_engine.environment.env import ViralScriptEnv
    from viral_script_engine.training.rollout_function import build_rollout_fn, build_training_prompts

    print("\n[DRY-RUN] Building curriculum prompts from live environment...")
    all_prompts = []
    for tier in tiers:
        try:
            prompts = build_training_prompts(tier)
            all_prompts.extend(prompts)
            print(f"  Loaded {len(prompts)} prompts from {tier}_tier.jsonl")
        except FileNotFoundError as e:
            print(f"  WARNING: {e}")
            print(f"  Skipping {tier} tier — run build_curriculum.py to generate JSONL files.")

    if not all_prompts:
        print("  No curriculum files found. Falling back to live env random reset...")
        env = ViralScriptEnv(
            scripts_path=str(BASE_DIR / "data" / "test_scripts" / "scripts.json"),
            cultural_kb_path=str(BASE_DIR / "data" / "cultural_kb.json"),
            max_steps=5,
            difficulty="easy",
        )
        all_prompts = ["##LIVE_ENV_FALLBACK##"] * steps
        dry_run_env = env
    else:
        dry_run_env = ViralScriptEnv(
            scripts_path=str(BASE_DIR / "data" / "test_scripts" / "scripts.json"),
            cultural_kb_path=str(BASE_DIR / "data" / "cultural_kb.json"),
            max_steps=5,
            difficulty="easy",
        )

    rollout_fn = build_rollout_fn(dry_run_env, max_steps=5)
    mock_model = _DryRunModel()

    print(f"\n[DRY-RUN] Running {steps} steps through live ViralScriptEnv...\n")

    training_log = []
    for step in range(steps):
        prompt = all_prompts[step % len(all_prompts)]
        completions, rewards = rollout_fn([prompt], model=mock_model, tokenizer=None)
        reward = rewards[0]
        training_log.append({"step": step + 1, "reward": reward})
        print(f"  Step {step + 1}/{steps} | reward={reward:.4f} | env=live")

    log_path = LOGS_DIR / "dry_run_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(training_log, f, indent=2)

    mean_reward = sum(r["reward"] for r in training_log) / len(training_log)
    print(f"\n  Mean reward across {steps} steps: {mean_reward:.4f}")
    print(f"  Log saved -> {log_path}")
    print("\nPHASE 3 GATE: PASS — Dry run complete. Training pipeline connected to live environment.")


# ---------------------------------------------------------------------------
# Full training (GPU required)
# ---------------------------------------------------------------------------

def run_full_training(
    tiers: list,
    steps: int,
    model_name: str,
    output_dir: str,
    enable_wandb: bool,
):
    from viral_script_engine.environment.env import ViralScriptEnv
    from viral_script_engine.training.rollout_function import build_rollout_fn, build_training_prompts

    if enable_wandb and not os.getenv("WANDB_API_KEY"):
        print("WARNING: --wandb set but WANDB_API_KEY not found in env. Disabling WandB.")
        enable_wandb = False

    if enable_wandb:
        os.environ["WANDB_PROJECT"] = "viral-script-grpo"

    print(f"[TRAINING] Loading model: {model_name}")
    model, tokenizer = load_model(model_name)

    env = ViralScriptEnv(
        scripts_path=str(BASE_DIR / "data" / "test_scripts" / "scripts.json"),
        cultural_kb_path=str(BASE_DIR / "data" / "cultural_kb.json"),
        max_steps=5,
        difficulty=tiers[0] if tiers else "easy",
    )

    rollout_fn = build_rollout_fn(env, max_steps=5)

    all_prompts = []
    for tier in tiers:
        prompts = build_training_prompts(tier)
        all_prompts.extend(prompts)
        print(f"  Loaded {len(prompts)} prompts from {tier}_tier.jsonl")

    from trl import GRPOTrainer
    from datasets import Dataset

    dataset = Dataset.from_dict({"prompt": all_prompts})
    config = build_grpo_config(output_dir, steps, dry_run=False)

    trainer = GRPOTrainer(
        model=model,
        tokenizer=tokenizer,
        config=config,
        train_dataset=dataset,
        reward_funcs=rollout_fn,
    )

    print(f"\n[TRAINING] Starting GRPO training for {steps} steps...")
    trainer.train()

    print(f"\n[TRAINING] Saving model to {output_dir}/final_model ...")
    model.save_pretrained_merged(
        f"{output_dir}/final_model",
        tokenizer,
        save_method="merged_16bit",
    )
    print("[TRAINING] Done.")


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="GRPO Training — Viral Script Debugging Engine")
    parser.add_argument("--tier", default="easy", help="Comma-separated tiers: easy,medium,hard")
    parser.add_argument("--steps", type=int, default=200, help="Number of training steps")
    parser.add_argument("--dry-run", action="store_true", help="Validate pipeline (5 steps, no GPU)")
    parser.add_argument("--model", default="unsloth/Qwen2.5-7B-Instruct-bnb-4bit",
                        help="Base model for full training")
    parser.add_argument("--output-dir", default="outputs/checkpoints", help="Checkpoint directory")
    parser.add_argument("--wandb", action="store_true", help="Enable WandB logging")
    return parser.parse_args()


def main():
    args = parse_args()
    tiers = [t.strip() for t in args.tier.split(",") if t.strip()]
    output_dir = str(BASE_DIR.parent / args.output_dir)

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("GRPO Training — Viral Script Debugging Engine")
    print(f"  Tiers:      {tiers}")
    print(f"  Steps:      {5 if args.dry_run else args.steps}")
    print(f"  Dry-run:    {args.dry_run}")
    print(f"  Model:      {'[mock]' if args.dry_run else args.model}")
    print(f"  Output dir: {output_dir}")
    print("=" * 60)

    if args.dry_run:
        run_dry_run(tiers, steps=5, output_dir=output_dir)
    else:
        run_full_training(
            tiers=tiers,
            steps=args.steps,
            model_name=args.model,
            output_dir=output_dir,
            enable_wandb=args.wandb,
        )


if __name__ == "__main__":
    main()
