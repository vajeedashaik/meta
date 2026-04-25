#!/usr/bin/env python3
"""
Evaluate the trained Arbitrator model on the same 20-episode schedule as the baseline.
Saves results to logs/trained_results.json, then generates training_vs_baseline.png.

Usage:
  python training/eval_trained_model.py --model outputs/checkpoints/final_model
"""
import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

_SCHEDULE = (
    [(i, "easy") for i in range(1, 9)]
    + [(i, "medium") for i in range(9, 17)]
    + [(i, "hard") for i in range(17, 21)]
)


def _make_env(difficulty: str):
    from viral_script_engine.environment.env import ViralScriptEnv
    return ViralScriptEnv(
        scripts_path=str(BASE_DIR / "data" / "test_scripts" / "scripts.json"),
        cultural_kb_path=str(BASE_DIR / "data" / "cultural_kb.json"),
        max_steps=5,
        difficulty=difficulty,
    )


def _load_trained_agent(model_path: str):
    """
    Load a fine-tuned model and return a callable agent.
    Uses unsloth FastLanguageModel if available; falls back to a HuggingFace pipeline.
    """
    model_path = Path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(f"Trained model not found: {model_path}")

    try:
        from unsloth import FastLanguageModel
        model, tokenizer = FastLanguageModel.from_pretrained(
            str(model_path), max_seq_length=2048, dtype=None, load_in_4bit=True
        )
        FastLanguageModel.for_inference(model)
        return _HFAgent(model, tokenizer)
    except ImportError:
        pass

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
        tokenizer = AutoTokenizer.from_pretrained(str(model_path))
        model = AutoModelForCausalLM.from_pretrained(str(model_path))
        pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)
        return _PipelineAgent(pipe)
    except Exception as e:
        raise RuntimeError(f"Could not load trained model: {e}")


class _HFAgent:
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer

    def act(self, observation: dict) -> dict:
        from viral_script_engine.training.rollout_function import (
            _format_observation_prompt, _extract_json_action, _model_generate,
        )
        prompt = _format_observation_prompt(observation, observation.get("step_num", 1), 5)
        raw = _model_generate(self.model, self.tokenizer, prompt, max_new_tokens=256)
        return _extract_json_action(raw)


class _PipelineAgent:
    def __init__(self, pipe):
        self.pipe = pipe

    def act(self, observation: dict) -> dict:
        import json
        from viral_script_engine.training.rollout_function import (
            _format_observation_prompt, _extract_json_action,
        )
        prompt = _format_observation_prompt(observation, observation.get("step_num", 1), 5)
        out = self.pipe(prompt, max_new_tokens=256, return_full_text=False)
        raw = out[0]["generated_text"] if out else ""
        return _extract_json_action(raw)


def run_episode(ep_num: int, difficulty: str, agent) -> dict:
    env = _make_env(difficulty)
    obs, _ = env.reset()

    episode_id = obs["episode_id"]
    state = env.state()
    original_script = state.get("original_script", "")

    steps_log = []
    total_reward = 0.0

    for _ in range(env.max_steps):
        action = agent.act(obs)
        obs, reward, terminated, truncated, info = env.step(action)
        rc = info["reward_components"]
        anti_log = info.get("anti_gaming_log", {})

        steps_log.append({
            "r1": rc.get("r1_hook_strength"),
            "r2": rc.get("r2_coherence"),
            "r3": rc.get("r3_cultural_alignment"),
            "r4": rc.get("r4_debate_resolution"),
            "r5": rc.get("r5_defender_preservation"),
            "total": reward,
            "anti_gaming_triggered": anti_log.get("triggered", False),
            "penalty": anti_log.get("penalty_applied", 0.0),
        })
        total_reward = reward

        if terminated or truncated:
            break

    final_state = env.state()
    return {
        "episode_num": ep_num,
        "episode_id": episode_id,
        "difficulty": difficulty,
        "steps": steps_log,
        "total_reward": total_reward,
        "anti_gaming_logs": final_state.get("anti_gaming_logs", []),
        "original_script": original_script,
        "final_script": final_state.get("current_script", ""),
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate trained Arbitrator model")
    parser.add_argument("--model", required=True, help="Path to trained model directory")
    parser.add_argument("--output", default="logs/trained_results.json",
                        help="Output JSON path")
    args = parser.parse_args()

    print(f"Loading trained model from: {args.model}")
    agent = _load_trained_agent(args.model)

    all_episodes = []
    print("Running 20 evaluation episodes (same schedule as baseline)...")
    for ep_num, difficulty in _SCHEDULE:
        print(f"  Episode {ep_num:02d}/20 ({difficulty})...")
        try:
            result = run_episode(ep_num, difficulty, agent)
            all_episodes.append(result)
            print(f"    -> total_reward={result['total_reward']:.3f}  steps={len(result['steps'])}")
        except Exception as e:
            print(f"    ERROR episode {ep_num}: {e}")
            all_episodes.append({
                "episode_num": ep_num,
                "difficulty": difficulty,
                "steps": [],
                "total_reward": 0.0,
                "anti_gaming_logs": [],
                "original_script": "",
                "final_script": "",
                "error": str(e),
            })

    output_path = BASE_DIR / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_episodes, f, indent=2, default=str)
    print(f"\nSaved -> {output_path}")

    from viral_script_engine.training.reward_curves import plot_training_curves
    baseline_path = str(LOGS_DIR / "baseline_results.json")
    plot_training_curves(
        baseline_log_path=baseline_path,
        training_log_path=str(output_path),
        output_path=str(LOGS_DIR / "training_vs_baseline.png"),
    )


if __name__ == "__main__":
    main()
