from typing import List

from viral_script_engine.agents.critic import CritiqueClaim
from viral_script_engine.agents.defender import DefenderOutput
from viral_script_engine.environment.actions import ArbitratorAction
from viral_script_engine.environment.observations import RewardComponents

_SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}

_SECTION_KEYWORDS = {
    "hook": ["hook", "opening", "start", "first", "beginning", "intro"],
    "body": ["body", "middle", "main", "content"],
    "cta": ["cta", "call to action", "call-to-action", "ending", "end", "conclusion"],
}


class ProcessVerifier:
    """
    Checks whether the Arbitrator's reasoning chain is correct BEFORE
    the action is executed. This is process supervision.

    Three checks, each independently scored.
    """

    def verify_priority_assessment(
        self,
        priority_assessment: str,
        critic_claims: List[CritiqueClaim],
        current_reward_components: RewardComponents,
    ) -> float:
        """
        Checks: does priority_assessment mention the critique_class with
        the highest severity in the current Critic output?

        Score:
        - 1.0: mentions the highest-severity critique_class
        - 0.5: mentions a medium-severity class (not the worst, but not random)
        - 0.0: mentions only a low-severity class or is empty
        """
        if not priority_assessment or not critic_claims:
            return 0.0

        sorted_claims = sorted(
            critic_claims,
            key=lambda c: _SEVERITY_RANK.get(c.severity.lower(), 0),
            reverse=True,
        )

        assessment_lower = priority_assessment.lower()
        highest_class = sorted_claims[0].critique_class.lower()

        if highest_class in assessment_lower:
            return 1.0

        medium_classes = {
            c.critique_class.lower()
            for c in sorted_claims
            if c.severity.lower() == "medium"
        }
        if any(cls in assessment_lower for cls in medium_classes):
            return 0.5

        return 0.0

    def verify_conflict_check(
        self,
        conflict_check_answer: str,
        conflict_check_reason: str,
        action: ArbitratorAction,
        current_reward_components: RewardComponents,
        episode_start_components: RewardComponents,
    ) -> float:
        """
        Checks: is conflict_check_answer consistent with the actual risk?

        Known conflict patterns:
        - hook_rewrite when r3 >= 0.7 → conflict likely
        - section_reorder when r2 <= 0.6 → conflict likely
        - cultural_ref_sub when r5 <= 0.5 → conflict likely
        - cta_placement when r1 <= 0.4 → conflict likely

        Score:
        - 1.0: answer matches rule-based assessment
        - 0.0: answer contradicts it or is empty
        """
        if not conflict_check_answer:
            return 0.0

        action_type = action.action_type.value
        r1 = current_reward_components.r1_hook_strength or 0.0
        r2 = current_reward_components.r2_coherence or 0.0
        r3 = current_reward_components.r3_cultural_alignment or 0.0
        r5 = current_reward_components.r5_defender_preservation or 0.0

        conflict_exists = False
        if action_type == "hook_rewrite" and r3 >= 0.7:
            conflict_exists = True
        elif action_type == "section_reorder" and r2 <= 0.6:
            conflict_exists = True
        elif action_type == "cultural_ref_sub" and r5 <= 0.5:
            conflict_exists = True
        elif action_type == "cta_placement" and r1 <= 0.4:
            conflict_exists = True

        model_says_conflict = conflict_check_answer.lower().strip().startswith("yes")
        return 1.0 if model_says_conflict == conflict_exists else 0.0

    def verify_defender_consideration(
        self,
        defender_consideration_answer: str,
        defender_consideration_reason: str,
        action: ArbitratorAction,
        defender_output: DefenderOutput,
    ) -> float:
        """
        Checks: if the action targets the same section as the Defender's
        core_strength_quote, did the Arbitrator say defender_consideration = "yes"?

        Score:
        - 1.0: answer is correct
        - 0.0: answer is wrong or empty
        """
        if not defender_consideration_answer:
            return 0.0

        core_quote_lower = defender_output.core_strength_quote.lower()
        target_section = action.target_section.lower()

        # Infer which section the core strength resides in
        core_section = None
        for section, keywords in _SECTION_KEYWORDS.items():
            if any(kw in core_quote_lower for kw in keywords):
                core_section = section
                break

        # target_section "full" always overlaps with core strength
        if target_section == "full":
            target_matches_core = True
        elif core_section is not None:
            target_matches_core = (
                target_section == core_section
                or target_section in core_section
                or core_section in target_section
            )
        else:
            # Cannot determine core section — give benefit of doubt based on exact match
            target_matches_core = target_section in core_quote_lower

        model_says_yes = defender_consideration_answer.lower().strip().startswith("yes")
        return 1.0 if model_says_yes == target_matches_core else 0.0
