"""
Rollout function bridging TRL's GRPOTrainer to the live ViralScriptEnv.

Each call:
  1. Parses episode config from the prompt metadata header
  2. Resets env with that config (live environment — not a static dataset)
  3. Generates an action via the model (JSON)
  4. Steps through the env for up to max_steps
  5. Returns completions and final episode rewards
"""
import json
import re
import sys
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from viral_script_engine.environment.env import ViralScriptEnv

_FALLBACK_ACTION = {
    "action_type": "hook_rewrite",
    "target_section": "hook",
    "instruction": "Rewrite the hook to open with a strong immediate claim.",
    "critique_claim_id": "C1",
    "reasoning": "Default fallback when model output is not valid JSON.",
}

_VALID_ACTIONS = {"hook_rewrite", "section_reorder", "cultural_ref_sub", "cta_placement"}

ARBITRATOR_SYSTEM = (
    "You are an expert content strategist acting as an Arbitrator in a script improvement debate.\n"
    "You observe a debate between a Critic and Defender about a creator's script.\n"
    "You must choose exactly ONE action to improve the script.\n\n"
    "AVAILABLE ACTIONS: hook_rewrite | section_reorder | cultural_ref_sub | cta_placement\n\n"
    'OUTPUT FORMAT (JSON only):\n'
    '{"action_type": "...", "target_section": "...", "instruction": "...", '
    '"critique_claim_id": "...", "reasoning": "..."}'
)


def _format_observation_prompt(obs: dict, step_num: int, max_steps: int) -> str:
    current_script = obs.get("current_script", "")
    region = obs.get("region", "")
    platform = obs.get("platform", "")
    niche = obs.get("niche", "")
    rc = obs.get("reward_components", {})
    r1 = rc.get("r1_hook_strength") or 0.0
    r2 = rc.get("r2_coherence") or 0.0
    r3 = rc.get("r3_cultural_alignment", "N/A")
    r4 = rc.get("r4_debate_resolution", "N/A")
    r5 = rc.get("r5_defender_preservation", "N/A")

    debate = obs.get("debate_history", [])
    critic_text = "None"
    defender_text = "None"
    if debate:
        last = debate[-1]
        claims = last.get("critic_claims", [])
        critic_text = "\n".join(
            f"- [{c.get('claim_id','?')}] {c.get('claim_text','')} (severity: {c.get('severity','')})"
            for c in claims
        ) or "None"
        df = last.get("defender_response") or {}
        if df:
            defender_text = (
                f"Core strength: {df.get('core_strength_quote','')}\n"
                f"Defense: {df.get('defense_argument','')}\n"
                f"Flagged claims: {df.get('flagged_critic_claims', [])}"
            )

    return (
        f"<|system|>\n{ARBITRATOR_SYSTEM}\n<|end|>\n\n"
        f"<|user|>\n"
        f"CURRENT SCRIPT:\n{current_script}\n\n"
        f"REGION: {region} | PLATFORM: {platform} | NICHE: {niche}\n\n"
        f"CRITIC CLAIMS:\n{critic_text}\n\n"
        f"DEFENDER RESPONSE:\n{defender_text}\n\n"
        f"CURRENT REWARDS: R1={r1:.2f} R2={r2:.2f} R3={r3} R4={r4} R5={r5}\n"
        f"STEP: {step_num}/{max_steps}\n\n"
        "Choose your action:\n<|end|>"
    )


def _extract_json_action(text: str) -> dict:
    text = text.strip()
    # strip markdown fences
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    # find first {...}
    match = re.search(r"\{.*?\}", text, re.DOTALL)
    if match:
        try:
            action = json.loads(match.group())
            if action.get("action_type") in _VALID_ACTIONS:
                return action
        except json.JSONDecodeError:
            pass
    return _FALLBACK_ACTION.copy()


def _model_generate(model, tokenizer, prompt: str, max_new_tokens: int = 256) -> str:
    """
    Generate text from the model. Works with HuggingFace-style models.
    Falls back gracefully if model has no standard generate() (e.g., mock models).
    """
    if hasattr(model, "generate") and hasattr(tokenizer, "encode"):
        import torch
        inputs = tokenizer(prompt, return_tensors="pt")
        input_ids = inputs["input_ids"]
        if hasattr(model, "device"):
            input_ids = input_ids.to(model.device)
        with torch.no_grad():
            outputs = model.generate(
                input_ids,
                max_new_tokens=max_new_tokens,
                temperature=0.8,
                top_p=0.9,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )
        new_tokens = outputs[0][input_ids.shape[-1]:]
        return tokenizer.decode(new_tokens, skip_special_tokens=True)
    elif callable(model):
        return model(prompt)
    else:
        raise ValueError(f"Model type {type(model)} is not supported.")


def build_rollout_fn(
    env: ViralScriptEnv,
    max_steps: int = 5,
    max_new_tokens: int = 256,
):
    """
    Returns a rollout function compatible with TRL's GRPOTrainer interface.

    Each prompt is expected to contain an embedded episode config JSON in a header:
      ##EPISODE_CONFIG## {...} ##END_CONFIG##

    This connects the training loop to the live OpenEnv environment.
    """

    def rollout_fn(
        prompts: List[str],
        model,
        tokenizer,
    ) -> Tuple[List[str], List[float]]:
        completions: List[str] = []
        rewards: List[float] = []

        for prompt in prompts:
            config = _parse_episode_config(prompt)

            if config:
                obs, _ = env.reset_from_config(config)
            else:
                obs, _ = env.reset()

            episode_completion_parts = []
            episode_reward = 0.0
            terminated = False
            truncated = False

            for step in range(max_steps):
                obs_prompt = _format_observation_prompt(obs, step + 1, max_steps)
                full_prompt = prompt + "\n\n" + obs_prompt

                raw_output = _model_generate(model, tokenizer, full_prompt, max_new_tokens)
                action = _extract_json_action(raw_output)
                episode_completion_parts.append(raw_output)

                try:
                    obs, reward, terminated, truncated, info = env.step(action)
                    episode_reward = reward
                except Exception:
                    # LLM agent (critic/defender) parse error — skip step, keep prior reward
                    terminated = True

                if terminated or truncated:
                    break

            completions.append("\n".join(episode_completion_parts))
            rewards.append(episode_reward)

        return completions, rewards

    return rollout_fn


def _parse_episode_config(prompt: str) -> dict:
    """Extract embedded episode config JSON from a prompt string."""
    match = re.search(r"##EPISODE_CONFIG##\s*(\{.*?\})\s*##END_CONFIG##", prompt, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return {}


def build_training_prompts(tier: str, curriculum_dir: str = None) -> List[str]:
    """
    Load a curriculum tier JSONL and convert to prompt strings with embedded episode configs.
    Used by train_grpo.py to build the training dataset.
    """
    if curriculum_dir is None:
        curriculum_dir = Path(__file__).parent.parent / "data" / "curriculum"
    else:
        curriculum_dir = Path(curriculum_dir)

    tier_file = curriculum_dir / f"{tier}_tier.jsonl"
    if not tier_file.exists():
        raise FileNotFoundError(
            f"Curriculum file not found: {tier_file}\n"
            "Run data/curriculum/build_curriculum.py first."
        )

    prompts = []
    with open(tier_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            config = json.loads(line)
            prompt = _config_to_prompt(config)
            prompts.append(prompt)

    return prompts


def _config_to_prompt(config: dict) -> str:
    """Convert an episode config into a training prompt with embedded config header."""
    config_json = json.dumps({
        "script_text": config["script_text"],
        "region": config["region"],
        "platform": config["platform"],
        "niche": config["niche"],
        "difficulty": config["difficulty"],
        "script_id": config["script_id"],
    })
    header = f"##EPISODE_CONFIG## {config_json} ##END_CONFIG##"

    return (
        f"{header}\n\n"
        f"<|system|>\n{ARBITRATOR_SYSTEM}\n<|end|>\n\n"
        f"<|user|>\n"
        f"CURRENT SCRIPT:\n{config['script_text']}\n\n"
        f"REGION: {config['region']} | PLATFORM: {config['platform']} | NICHE: {config['niche']}\n\n"
        f"DOMINANT FLAW: {config.get('dominant_flaw', 'unknown')}\n"
        f"CURRICULUM NOTES: {config.get('curriculum_notes', '')}\n\n"
        "Choose your action:\n<|end|>"
    )
