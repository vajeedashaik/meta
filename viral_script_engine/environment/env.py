import json
import random
from collections import Counter
from typing import Optional, Tuple

from viral_script_engine.agents.critic import CriticAgent
from viral_script_engine.agents.defender import DefenderAgent
from viral_script_engine.agents.rewriter import RewriterAgent
from viral_script_engine.agents.reasoning_parser import ReasoningParser, ArbitratorParseError
from viral_script_engine.environment.actions import ArbitratorAction
from viral_script_engine.environment.episode_state import EpisodeState
from viral_script_engine.environment.observations import (
    DebateRound, Observation, RewardComponents,
)
from viral_script_engine.agents.moderation_agent import ModerationAgent
from viral_script_engine.agents.originality_agent import OriginalityAgent
from viral_script_engine.rewards.r1_hook_strength import HookStrengthReward
from viral_script_engine.rewards.r2_coherence import CoherenceReward
from viral_script_engine.rewards.r3_cultural_alignment import CulturalAlignmentReward
from viral_script_engine.rewards.r4_debate_resolution import DebateResolutionReward
from viral_script_engine.rewards.r5_defender_preservation import DefenderPreservationReward
from viral_script_engine.rewards.r6_safety import SafetyReward
from viral_script_engine.rewards.r7_originality import OriginalityReward
from viral_script_engine.rewards.reward_aggregator import RewardAggregator
from viral_script_engine.rewards.process_reward import ProcessReward, ProcessRewardResult
from viral_script_engine.personas.creator_profile import CreatorProfile, CreatorTier
from viral_script_engine.personas.profile_generator import ProfileGenerator
from viral_script_engine.rewards.r8_persona_fit import PersonaFitReward
from viral_script_engine.rewards.r9_platform_pacing import PlatformPacingReward
from viral_script_engine.platforms.platform_spec import PlatformRegistry
from viral_script_engine.memory.memory_compressor import MemoryCompressor
from viral_script_engine.memory.history_store import HistoryStore
from viral_script_engine.rewards.r10_retention_curve import RetentionCurveReward

_TIERS = {
    "easy": ["S01", "S02", "S03", "S04"],
    "medium": ["S05", "S06", "S07"],
    "hard": ["S08", "S09", "S10"],
    "self_generated": [],
}


class ViralScriptEnv:
    def __init__(
        self,
        scripts_path: str = "data/test_scripts/scripts.json",
        max_steps: int = 5,
        difficulty: str = "easy",
        use_anti_gaming: bool = True,
        cultural_kb_path: str = "data/cultural_kb.json",
        use_escalation: bool = True,
        difficulty_tracker=None,
        escalation_engine=None,
    ):
        self.max_steps = max_steps
        self.difficulty = difficulty
        self.use_anti_gaming = use_anti_gaming
        self.use_escalation = use_escalation

        with open(scripts_path) as f:
            all_scripts = json.load(f)

        tier_ids = _TIERS.get(difficulty, [])
        self._scripts = [s for s in all_scripts if s["script_id"] in tier_ids]
        if not self._scripts:
            self._scripts = all_scripts

        self.critic = CriticAgent()
        self.defender = DefenderAgent()
        self.rewriter = RewriterAgent()
        self.r1 = HookStrengthReward()
        self.r2 = CoherenceReward()
        self.r3 = CulturalAlignmentReward(knowledge_base_path=cultural_kb_path)
        self.r4 = DebateResolutionReward(critic_agent=self.critic)
        self.r5 = DefenderPreservationReward()
        self.r6 = SafetyReward()
        self.r7 = OriginalityReward()
        self.moderation_agent = ModerationAgent()
        self.originality_agent = OriginalityAgent()
        self.aggregator = RewardAggregator()
        self.reasoning_parser = ReasoningParser()
        self.process_reward_calc = ProcessReward()
        self.profile_generator = ProfileGenerator()
        self.r8 = PersonaFitReward()
        self.r9 = PlatformPacingReward()
        self.platform_registry = PlatformRegistry()
        self.memory_compressor = MemoryCompressor()
        self.history_store = HistoryStore()
        self.r10 = RetentionCurveReward(cultural_kb_path=cultural_kb_path)
        self._state: Optional[EpisodeState] = None
        self._current_profile: Optional[CreatorProfile] = None
        self._current_platform: str = "Reels"
        self._current_creator_id: str = "default"
        self._current_history_buffer = None

        if use_escalation:
            if difficulty_tracker is None:
                from viral_script_engine.escalation.difficulty_tracker import DifficultyTracker
                difficulty_tracker = DifficultyTracker()
            if escalation_engine is None:
                from viral_script_engine.escalation.critic_escalation_engine import CriticEscalationEngine
                escalation_engine = CriticEscalationEngine()

        self.difficulty_tracker = difficulty_tracker
        self.escalation_engine = escalation_engine

        # Track first-step critic output per episode for dominant class detection
        self._first_critique = None

    def reset_from_config(self, episode_config: dict) -> Tuple[dict, dict]:
        """Reset the environment to a specific episode config from curriculum JSONL."""
        script = {
            "script_id": episode_config.get("script_id", "unknown"),
            "script_text": episode_config["script_text"],
            "region": episode_config["region"],
            "platform": episode_config["platform"],
            "niche": episode_config["niche"],
        }
        return self._reset_with_script(script, episode_config.get("difficulty", self.difficulty))

    def reset(self, seed=None, options=None) -> Tuple[dict, dict]:
        if seed is not None:
            random.seed(seed)

        self._first_critique = None
        used_escalation = False

        if self.use_escalation and self.difficulty_tracker and self.escalation_engine:
            mastered = self.difficulty_tracker.get_mastered_classes()
            if mastered:
                challenge = self.escalation_engine.get_next_challenge(self.difficulty_tracker)
                if challenge is None:
                    # Generate a new escalated challenge from the first mastered class
                    src_class = mastered[0]
                    example_script = random.choice(self._scripts)
                    challenge = self.escalation_engine.escalate(
                        mastered_class=src_class,
                        original_script_example=example_script["script_text"],
                        region=example_script.get("region", "pan_india_english"),
                        platform=example_script.get("platform", "Reels"),
                    )

                script = challenge.to_script_dict()
                print(f"[ESCALATION] Using self-generated challenge for class '{challenge.source_class}' — {challenge.why_its_harder}")
                obs, info = self._reset_with_script(script, "self_generated")
                info["escalation_used"] = True
                info["escalation_source_class"] = challenge.source_class
                return obs, info

        script = random.choice(self._scripts)
        obs, info = self._reset_with_script(script, self.difficulty)
        info["escalation_used"] = False
        return obs, info

    def _reset_with_script(self, script: dict, difficulty: str) -> Tuple[dict, dict]:
        self._current_creator_id = script.get("creator_id", script.get("script_id", "default"))
        self._current_history_buffer = self.history_store.load(self._current_creator_id)
        self._current_platform = script.get("platform", "Reels")
        r1_result = self.r1.score(script["script_text"], platform=self._current_platform)
        r2_result = self.r2.score(script["script_text"], script["script_text"], platform=self._current_platform)
        r3_result = self.r3.score(script["script_text"], script.get("region", "pan_india_english"))
        mod_out = self.moderation_agent.check(script["script_text"])
        orig_out = self.originality_agent.check(script["script_text"])
        r6_result = self.r6.score(mod_out)
        r7_result = self.r7.score(orig_out)
        initial_rewards = RewardComponents(
            r1_hook_strength=r1_result.score,
            r2_coherence=r2_result.score,
            r3_cultural_alignment=r3_result.score,
            r6_safety=r6_result.score,
            r7_originality=r7_result.score,
        )
        initial_rewards.compute_total()

        self._state = EpisodeState.new(
            script=script,
            max_steps=self.max_steps,
            difficulty_level=difficulty,
            initial_rewards=initial_rewards,
        )

        # Phase 8: generate a creator profile matching episode difficulty
        self._current_profile = self._generate_profile_for_difficulty(
            difficulty=difficulty,
            niche=script.get("niche", "personal finance"),
            seed=hash(script.get("script_id", "default")) % (2 ** 31),
        )

        return self._build_observation().model_dump(), {}

    def _generate_profile_for_difficulty(
        self, difficulty: str, niche: str, seed: int
    ) -> CreatorProfile:
        """Map episode difficulty to an appropriate creator tier."""
        tier_map = {
            "easy": [CreatorTier.BEGINNER, CreatorTier.GROWING],
            "medium": [CreatorTier.GROWING, CreatorTier.ESTABLISHED],
            "hard": [CreatorTier.ESTABLISHED, CreatorTier.VERIFIED],
            "self_generated": [CreatorTier.ESTABLISHED, CreatorTier.VERIFIED],
        }
        import random as _rng
        tiers = tier_map.get(difficulty, [CreatorTier.GROWING])
        tier = _rng.Random(seed).choice(tiers)
        return self.profile_generator.generate(tier=tier, niche=niche, seed=seed)

    def step(self, action: dict, raw_output: str = None) -> Tuple[dict, float, bool, bool, dict]:
        if self._state is None:
            raise RuntimeError("Call reset() before step()")

        arb_action = ArbitratorAction(**action)

        critique = self.critic.critique(
            script=self._state.current_script,
            region=self._state.region,
            platform=self._state.platform,
            niche=self._state.niche,
        )

        # Track first critique for dominant class detection at episode end
        if self._state.step_num == 0:
            self._first_critique = critique

        defender_output = self.defender.defend(
            script=self._state.current_script,
            critic_claims=critique.claims,
            region=self._state.region,
            platform=self._state.platform,
        )

        # Phase 7: parse reasoning chain and compute process reward before rewrite
        reasoning_chain = None
        process_result = None
        if raw_output:
            try:
                reasoning_chain = self.reasoning_parser.parse(raw_output)
                process_result = self.process_reward_calc.score(
                    reasoning_chain=reasoning_chain,
                    critic_claims=critique.claims,
                    defender_output=defender_output,
                    current_reward_components=self._state.last_reward_components,
                    episode_start_components=self._state.episode_start_rewards,
                )
            except ArbitratorParseError:
                reasoning_chain = None
                process_result = None

        rewrite_result = self.rewriter.rewrite(self._state.current_script, arb_action)
        new_script = rewrite_result.rewritten_script

        r1_result = self.r1.score(new_script, platform=self._current_platform)
        r2_result = self.r2.score(self._state.original_script, new_script, platform=self._current_platform)
        r3_result = self.r3.score(new_script, self._state.region)

        targeted_claim = next(
            (c for c in critique.claims if c.claim_id == arb_action.critique_claim_id),
            critique.claims[0] if critique.claims else None,
        )
        r4_result = self.r4.score(
            new_script=new_script,
            original_action=arb_action,
            original_claim=targeted_claim,
            region=self._state.region,
            platform=self._state.platform,
            niche=self._state.niche,
        ) if targeted_claim else None

        r5_result = self.r5.score(defender_output, new_script)

        moderation_out = self.moderation_agent.check(new_script)
        originality_out = self.originality_agent.check(new_script)
        r6_result = self.r6.score(moderation_out)
        r7_result = self.r7.score(originality_out)

        # Phase 8: compute R8 persona fit
        r8_score = None
        if self._current_profile is not None and targeted_claim is not None:
            r8_result = self.r8.score(
                action=arb_action,
                creator_profile=self._current_profile,
                addressed_critique_class=targeted_claim.critique_class,
            )
            r8_score = r8_result.score

        # Phase 9: compute R9 platform pacing
        r9_result = self.r9.score(new_script, platform=self._current_platform)

        # Phase 12: compute R10 retention curve reward
        r10_score = None
        if self.r10.predictor._trained:
            try:
                r10_result = self.r10.score(
                    original_script=self._state.original_script,
                    rewritten_script=new_script,
                    platform=self._current_platform,
                    region=self._state.region,
                    action_type=str(arb_action.action_type.value),
                    episode_id=self._state.episode_id,
                )
                r10_score = r10_result.score
            except Exception:
                r10_score = None

        components = RewardComponents(
            r1_hook_strength=r1_result.score,
            r2_coherence=r2_result.score,
            r3_cultural_alignment=r3_result.score,
            r4_debate_resolution=r4_result.score if r4_result else None,
            r5_defender_preservation=r5_result.score,
            r6_safety=r6_result.score,
            r7_originality=r7_result.score,
            r8_persona_fit=r8_score,
            r9_platform_pacing=r9_result.score,
            r10_retention_curve=r10_score,
            process_reward=process_result.weighted_contribution if process_result else None,
        )

        self._state.action_history.append(arb_action.action_type)
        if self.use_anti_gaming:
            components, anti_log = self.aggregator.compute(
                components,
                self._state.episode_start_rewards,
                self._state.action_history,
                episode_id=self._state.episode_id,
                step_num=self._state.step_num,
            )
        else:
            components.compute_total()
            from viral_script_engine.rewards.reward_aggregator import AntiGamingLog
            anti_log = AntiGamingLog(
                episode_id=self._state.episode_id,
                step_num=self._state.step_num,
                triggered=False,
                penalty_applied=0.0,
                pre_penalty_total=components.total,
                post_penalty_total=components.total,
            )

        round_ = DebateRound(
            step_num=self._state.step_num,
            critic_claims=critique.claims,
            defender_response=defender_output.model_dump(),
            arbitrator_action=arb_action,
            rewrite_diff=rewrite_result.diff,
            reward_components=components,
            moderation_output=moderation_out.model_dump(),
            originality_output=originality_out.model_dump(),
            reasoning_chain=reasoning_chain.model_dump() if reasoning_chain else None,
        )
        self._state.debate_history.append(round_)
        self._state.current_script = new_script
        self._state.last_reward_components = components
        self._state.step_num += 1

        if not hasattr(self._state, "anti_gaming_logs"):
            self._state.anti_gaming_logs = []
        self._state.anti_gaming_logs.append(anti_log.model_dump())

        terminated = (
            self._state.step_num >= self._state.max_steps
            or components.total >= 0.9
        )

        if terminated and self.use_escalation and self.difficulty_tracker:
            dominant_class = self._get_dominant_critique_class()
            r4_score = components.r4_debate_resolution if components.r4_debate_resolution is not None else 0.0
            self.difficulty_tracker.record_episode(
                dominant_critique_class=dominant_class,
                r4_score=r4_score,
                episode_id=self._state.episode_id,
            )

        if terminated:
            episode_number = (
                (self._current_history_buffer.total_episodes + 1)
                if self._current_history_buffer else 1
            )
            new_memory = self.memory_compressor.compress(
                episode_log=self._build_episode_log(),
                episode_number=episode_number,
            )
            self._current_history_buffer = self.memory_compressor.update_buffer(
                self._current_history_buffer, new_memory, self._current_creator_id
            )
            self.history_store.save(self._current_history_buffer)

        info = {
            "reward_components": components.model_dump(),
            "anti_gaming_triggered": anti_log.triggered,
            "penalty_reason": anti_log.rule_triggered,
            "anti_gaming_log": anti_log.model_dump(),
            "moderation_output": moderation_out.model_dump(),
            "originality_output": originality_out.model_dump(),
            "process_reward_result": process_result.model_dump() if process_result else None,
            "reasoning_chain": reasoning_chain.model_dump() if reasoning_chain else None,
            "creator_profile": self._current_profile.model_dump(mode="json") if self._current_profile else None,
        }
        return self._build_observation().model_dump(), components.total, terminated, False, info

    def _build_episode_log(self) -> dict:
        s = self._state
        first_claims = []
        if self._first_critique and self._first_critique.claims:
            first_claims = [c.model_dump() for c in self._first_critique.claims]
        return {
            "episode_id": s.episode_id,
            "niche": s.niche,
            "platform": s.platform,
            "actions_taken": [a.value if hasattr(a, "value") else str(a) for a in s.action_history],
            "first_critique_claims": first_claims,
            "initial_reward_components": s.episode_start_rewards.model_dump(),
            "final_reward_components": s.last_reward_components.model_dump(),
            "final_total_reward": s.last_reward_components.total,
        }

    def _get_dominant_critique_class(self) -> str:
        """Return the most common critique_class from the first episode critique."""
        if self._first_critique is None or not self._first_critique.claims:
            return "hook_weakness"
        counts = Counter(c.critique_class for c in self._first_critique.claims)
        return counts.most_common(1)[0][0]

    def state(self) -> dict:
        if self._state is None:
            return {}
        s = self._state
        return {
            "current_script": s.current_script,
            "original_script": s.original_script,
            "debate_history": [r.model_dump() for r in s.debate_history],
            "reward_components": s.last_reward_components.model_dump(),
            "step_num": s.step_num,
            "difficulty_level": s.difficulty_level,
            "episode_id": s.episode_id,
            "anti_gaming_logs": getattr(s, "anti_gaming_logs", []),
            "creator_profile": self._current_profile.model_dump(mode="json") if self._current_profile else None,
        }

    def _build_observation(self) -> Observation:
        s = self._state
        last_round = s.debate_history[-1] if s.debate_history else None
        mod_flags = []
        orig_flags = []
        if last_round and last_round.moderation_output:
            mod_flags = last_round.moderation_output.get("flags", [])
        if last_round and last_round.originality_output:
            orig_flags = last_round.originality_output.get("flags", [])
        history_context = (
            self._current_history_buffer.to_prompt_context()
            if self._current_history_buffer else None
        )
        return Observation(
            current_script=s.current_script,
            original_script=s.original_script,
            region=s.region,
            platform=s.platform,
            niche=s.niche,
            step_num=s.step_num,
            max_steps=s.max_steps,
            debate_history=s.debate_history,
            reward_components=s.last_reward_components,
            difficulty_level=s.difficulty_level,
            episode_id=s.episode_id,
            current_moderation_flags=mod_flags,
            current_originality_flags=orig_flags,
            creator_profile=self._current_profile.model_dump(mode="json") if self._current_profile else None,
            creator_history=self._current_history_buffer.model_dump() if self._current_history_buffer else None,
            history_context=history_context,
        )
