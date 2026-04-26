from __future__ import annotations
import json
import random
import uuid
from typing import Optional, Tuple

from viral_script_engine.environment.env import ViralScriptEnv
from viral_script_engine.environment.trajectory import Trajectory, TrajectoryType
from viral_script_engine.rewards.contrastive_reward import ContrastiveReward


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
        cultural_kb_path: str = "data/cultural_kb.json",
        max_steps: int = 5,
        difficulty: str = "easy",
    ):
        self.env_a = ViralScriptEnv(
            scripts_path=scripts_path,
            cultural_kb_path=cultural_kb_path,
            max_steps=max_steps,
            difficulty=difficulty,
            use_escalation=False,
            use_anti_gaming=False,
        )
        self.env_b = ViralScriptEnv(
            scripts_path=scripts_path,
            cultural_kb_path=cultural_kb_path,
            max_steps=max_steps,
            difficulty=difficulty,
            use_escalation=False,
            use_anti_gaming=False,
        )
        self.contrastive_reward_calc = ContrastiveReward()
        self._traj_a: Optional[Trajectory] = None
        self._traj_b: Optional[Trajectory] = None
        self._episode_id: Optional[str] = None
        self._step_num: int = 0
        self._forced_action_a: Optional[dict] = None
        self._forced_action_b: Optional[dict] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reset(self, seed=None, options=None) -> dict:
        """
        Reset BOTH environments with the SAME script and seed.
        Run step 1 automatically with the forced actions.
        Return the state after forced step 1.
        """
        if seed is None:
            seed = random.randint(0, 2 ** 31)

        self._episode_id = str(uuid.uuid4())
        self._step_num = 0

        obs_a, _ = self.env_a.reset(seed=seed)
        obs_b, _ = self.env_b.reset(seed=seed)

        return self._run_forced_step_1(obs_a, obs_b)

    def reset_from_script_id(self, script_id: str, scripts_path: str) -> dict:
        """Reset both environments to a specific script by ID."""
        with open(scripts_path) as f:
            all_scripts = json.load(f)
        script = next((s for s in all_scripts if s["script_id"] == script_id), None)
        if script is None:
            raise ValueError(f"Script {script_id!r} not found in {scripts_path}")

        self._episode_id = str(uuid.uuid4())
        self._step_num = 0

        episode_config = {
            "script_id": script["script_id"],
            "script_text": script["script_text"],
            "region": script["region"],
            "platform": script["platform"],
            "niche": script["niche"],
            "difficulty": script.get("difficulty", "hard"),
        }
        obs_a, _ = self.env_a.reset_from_config(episode_config)
        obs_b, _ = self.env_b.reset_from_config(episode_config)

        return self._run_forced_step_1(obs_a, obs_b)

    def step(self, action: dict) -> Tuple[dict, float, bool, bool, dict]:
        """
        Execute the action in BOTH environments simultaneously (step 2+).
        Same action applied to both trajectories.
        Returns combined observation with both trajectory states.
        Terminated when BOTH trajectories have reached max_steps.
        """
        if self._traj_a is None or self._traj_b is None:
            raise RuntimeError("Call reset() before step()")

        if not self._traj_a.terminated:
            obs_a, r_a, done_a, _, info_a = self.env_a.step(action)
            self._traj_a.current_script = obs_a.get(
                "current_script", self._traj_a.current_script
            )
            self._traj_a.cumulative_reward += r_a
            self._traj_a.step_count += 1
            self._traj_a.terminated = done_a
            self._traj_a.final_reward_components = info_a.get("reward_components")

        if not self._traj_b.terminated:
            obs_b, r_b, done_b, _, info_b = self.env_b.step(action)
            self._traj_b.current_script = obs_b.get(
                "current_script", self._traj_b.current_script
            )
            self._traj_b.cumulative_reward += r_b
            self._traj_b.step_count += 1
            self._traj_b.terminated = done_b
            self._traj_b.final_reward_components = info_b.get("reward_components")

        self._step_num += 1
        terminated = self._traj_a.terminated and self._traj_b.terminated

        episode_reward = 0.0
        if terminated:
            result = self.contrastive_reward_calc.compute(self._traj_a, self._traj_b)
            episode_reward = result.final_reward

        return self.state(), episode_reward, terminated, False, {}

    def state(self) -> dict:
        """
        Returns state showing both trajectories:
        {
          "trajectory_a": { current_script, reward_components, debate_history,
                            cumulative_reward, step_count, terminated, trajectory_type },
          "trajectory_b": { ... },
          "delta": traj_a.cumulative_reward - traj_b.cumulative_reward,
          "leading_trajectory": "A" or "B",
          "step_num": current step,
          "episode_id": ...
        }
        """
        if self._traj_a is None or self._traj_b is None:
            return {}

        delta = self._traj_a.cumulative_reward - self._traj_b.cumulative_reward
        leading = "A" if delta >= 0 else "B"

        return {
            "trajectory_a": self._traj_state(self.env_a, self._traj_a),
            "trajectory_b": self._traj_state(self.env_b, self._traj_b),
            "delta": delta,
            "leading_trajectory": leading,
            "step_num": self._step_num,
            "episode_id": self._episode_id,
        }

    def reward(self) -> float:
        """Called at episode end — returns the contrastive reward."""
        if self._traj_a is None or self._traj_b is None:
            return 0.0
        result = self.contrastive_reward_calc.compute(self._traj_a, self._traj_b)
        return result.final_reward

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_forced_step_1(self, obs_a: dict, obs_b: dict) -> dict:
        """
        After both envs are reset, run step 1 with forced actions and
        initialise the Trajectory objects.
        """
        initial_script = obs_a.get("current_script", "")
        region = obs_a.get("region", "pan_india_english")
        platform = obs_a.get("platform", "Reels")
        niche = obs_a.get("niche", "personal finance")

        self._traj_a = Trajectory(
            trajectory_id=f"{self._episode_id}_A",
            trajectory_type=TrajectoryType.CRITIC_FIRST,
            initial_script=initial_script,
            current_script=initial_script,
        )
        self._traj_b = Trajectory(
            trajectory_id=f"{self._episode_id}_B",
            trajectory_type=TrajectoryType.DEFENDER_FIRST,
            initial_script=initial_script,
            current_script=initial_script,
        )

        # Run critic and defender once to determine forced actions
        critique = self.env_a.critic.critique(
            script=initial_script,
            region=region,
            platform=platform,
            niche=niche,
        )
        defender_out = self.env_a.defender.defend(
            script=initial_script,
            critic_claims=critique.claims,
            region=region,
            platform=platform,
        )

        forced_a = self._traj_a.get_forced_first_action(critique.claims, defender_out)
        forced_b = self._traj_b.get_forced_first_action(critique.claims, defender_out)

        self._forced_action_a = forced_a
        self._forced_action_b = forced_b

        # Execute forced step 1 in each environment
        obs_a_new, r_a, done_a, _, info_a = self.env_a.step(forced_a)
        obs_b_new, r_b, done_b, _, info_b = self.env_b.step(forced_b)

        self._traj_a.current_script = obs_a_new.get("current_script", initial_script)
        self._traj_a.cumulative_reward = r_a
        self._traj_a.step_count = 1
        self._traj_a.terminated = done_a
        self._traj_a.final_reward_components = info_a.get("reward_components")

        self._traj_b.current_script = obs_b_new.get("current_script", initial_script)
        self._traj_b.cumulative_reward = r_b
        self._traj_b.step_count = 1
        self._traj_b.terminated = done_b
        self._traj_b.final_reward_components = info_b.get("reward_components")

        self._step_num = 1

        return self.state()

    def _traj_state(self, env: ViralScriptEnv, traj: Trajectory) -> dict:
        s = env.state()
        return {
            "current_script": traj.current_script,
            "reward_components": s.get("reward_components", {}),
            "debate_history": s.get("debate_history", []),
            "cumulative_reward": traj.cumulative_reward,
            "step_count": traj.step_count,
            "terminated": traj.terminated,
            "trajectory_type": traj.trajectory_type,
        }
