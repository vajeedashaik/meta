import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from viral_script_engine.environment.actions import ArbitratorAction
from viral_script_engine.personas.creator_profile import CreatorProfile


class PersonaFitResult(BaseModel):
    score: float
    tier_match: str          # "priority" | "neutral" | "deprioritised" | "forbidden"
    is_forbidden: bool
    recurring_weakness_bonus: float
    explanation: str


class PersonaFitReward:
    """
    Measures whether the Arbitrator's chosen action is appropriate
    for the creator's tier and profile.

    Scoring:
    - Action is in priority_actions for this tier:          1.0
    - Action is neutral (not priority AND not deprioritised): 0.5
    - Action is in deprioritised_actions for this tier:     0.2
    - Action is explicitly forbidden for this tier:         0.0

    Additionally, if past_weak_points contains the critique_class being
    addressed, add +0.1 bonus (the Arbitrator correctly targeting a known
    recurring issue). Cap total at 1.0.
    """

    def __init__(self, kb_path: Optional[str] = None):
        if kb_path is None:
            kb_path = str(Path(__file__).parent.parent / "data" / "persona_advice_kb.json")
        with open(kb_path, encoding="utf-8") as f:
            self._kb = json.load(f)

    def score(
        self,
        action: ArbitratorAction,
        creator_profile: CreatorProfile,
        addressed_critique_class: str,
    ) -> PersonaFitResult:
        tier = creator_profile.tier.value
        rules = self._kb.get(tier, {})

        priority_actions = rules.get("priority_actions", [])
        deprioritised_actions = rules.get("deprioritised_actions", [])
        forbidden_advice = rules.get("forbidden_advice", [])
        action_type = action.action_type.value

        # Check forbidden first
        is_forbidden = self._is_forbidden(action_type, forbidden_advice)
        if is_forbidden:
            return PersonaFitResult(
                score=0.0,
                tier_match="forbidden",
                is_forbidden=True,
                recurring_weakness_bonus=0.0,
                explanation=f"Action '{action_type}' is forbidden for {tier} creators.",
            )

        # Determine base score
        if action_type in priority_actions:
            base_score = 1.0
            tier_match = "priority"
        elif action_type in deprioritised_actions:
            base_score = 0.2
            tier_match = "deprioritised"
        else:
            base_score = 0.5
            tier_match = "neutral"

        # Recurring weakness bonus
        bonus = 0.0
        if addressed_critique_class in creator_profile.past_weak_points:
            bonus = 0.1

        final_score = min(1.0, base_score + bonus)
        explanation = (
            f"Action '{action_type}' is {tier_match} for {tier} tier."
            + (f" +0.1 bonus: targeting known weak point '{addressed_critique_class}'." if bonus else "")
        )

        return PersonaFitResult(
            score=final_score,
            tier_match=tier_match,
            is_forbidden=False,
            recurring_weakness_bonus=bonus,
            explanation=explanation,
        )

    def _is_forbidden(self, action_type: str, forbidden_advice: list) -> bool:
        for phrase in forbidden_advice:
            # Map action_type strings to forbidden phrases using substring match
            if action_type == "hook_rewrite" and any(
                kw in phrase for kw in ["hook", "change the hook", "simplify the hook"]
            ):
                return True
            if action_type == "cta_placement" and "add a CTA" in phrase:
                return True
        return False
