from __future__ import annotations
from typing import Any, List, Optional
from pydantic import BaseModel

from viral_script_engine.environment.observations import DebateRound, RewardComponents

_SEVERITY_ORDER = {"high": 3, "medium": 2, "low": 1}

_CRITIQUE_TO_ACTION = {
    "hook_weakness": "hook_rewrite",
    "pacing_issue": "section_reorder",
    "cultural_mismatch": "cultural_ref_sub",
    "cta_buried": "cta_placement",
    "coherence_break": "section_reorder",
    "retention_risk": "hook_rewrite",
}

_ACTION_TO_TARGET = {
    "hook_rewrite": "hook",
    "section_reorder": "body",
    "cultural_ref_sub": "body",
    "cta_placement": "cta",
}


class TrajectoryType:
    CRITIC_FIRST = "critic_first"      # Trajectory A: act on Critic's top claim first
    DEFENDER_FIRST = "defender_first"  # Trajectory B: act on Defender's concern first


class Trajectory(BaseModel):
    trajectory_id: str
    trajectory_type: str
    initial_script: str
    current_script: str
    steps: List[Any] = []
    cumulative_reward: float = 0.0
    final_reward_components: Optional[Any] = None
    terminated: bool = False
    step_count: int = 0

    def get_forced_first_action(
        self,
        critic_claims: List[Any],
        defender_output: Any,
    ) -> dict:
        """
        Returns the forced first action based on trajectory type.

        CRITIC_FIRST: pick the action that addresses the highest-severity CritiqueClaim.
        DEFENDER_FIRST: pick the action that preserves the core_strength_quote.
            If core_strength is in hook → hook_rewrite is risky → pick cta_placement first.
        """
        if self.trajectory_type == TrajectoryType.CRITIC_FIRST:
            return self._critic_first_action(critic_claims)
        return self._defender_first_action(critic_claims, defender_output)

    def _critic_first_action(self, critic_claims: List[Any]) -> dict:
        if not critic_claims:
            return _fallback_action("C1")
        sorted_claims = sorted(
            critic_claims,
            key=lambda c: _SEVERITY_ORDER.get(getattr(c, "severity", "low"), 0),
            reverse=True,
        )
        top = sorted_claims[0]
        action_type = _CRITIQUE_TO_ACTION.get(
            getattr(top, "critique_class", ""), "hook_rewrite"
        )
        return {
            "action_type": action_type,
            "target_section": _ACTION_TO_TARGET.get(action_type, "hook"),
            "instruction": (
                f"Address the top critic concern: "
                f"{getattr(top, 'claim_text', '')[:100]}"
            ),
            "critique_claim_id": getattr(top, "claim_id", "C1"),
            "reasoning": (
                f"CRITIC_FIRST: targeting highest-severity "
                f"{getattr(top, 'critique_class', '')} claim ({getattr(top, 'severity', '')})."
            ),
        }

    def _defender_first_action(self, critic_claims: List[Any], defender_output: Any) -> dict:
        core_quote = ""
        flagged: set = set()

        if defender_output is not None:
            if hasattr(defender_output, "core_strength_quote"):
                core_quote = defender_output.core_strength_quote or ""
                flagged = set(getattr(defender_output, "flagged_critic_claims", []))
            elif isinstance(defender_output, dict):
                core_quote = defender_output.get("core_strength_quote", "")
                flagged = set(defender_output.get("flagged_critic_claims", []))

        # Core strength is "in the hook" if its first 20 chars appear in the leading 100 chars
        hook_portion = self.current_script[:100].lower()
        core_in_hook = bool(core_quote) and core_quote.lower()[:20] in hook_portion

        if core_in_hook:
            # Hook is precious — choose a safe non-hook action first
            action_type = "cta_placement"
            target = "cta"
            instruction = (
                "Improve CTA positioning to boost completion rate "
                "without altering the hook."
            )
            claim_id = (
                getattr(critic_claims[0], "claim_id", "C1")
                if critic_claims else "C1"
            )
        else:
            # Core is in body — safe to improve the hook
            action_type = "hook_rewrite"
            target = "hook"
            instruction = (
                "Rewrite the hook for stronger attention capture "
                "while preserving the core body voice."
            )
            unflagged = [
                c for c in critic_claims
                if getattr(c, "claim_id", "") not in flagged
            ]
            claim = unflagged[0] if unflagged else (critic_claims[0] if critic_claims else None)
            claim_id = getattr(claim, "claim_id", "C1") if claim else "C1"

        return {
            "action_type": action_type,
            "target_section": target,
            "instruction": instruction,
            "critique_claim_id": claim_id,
            "reasoning": (
                "DEFENDER_FIRST: preserving Defender's core strength "
                "and regional voice before addressing critic claims."
            ),
        }


def _fallback_action(claim_id: str = "C1") -> dict:
    return {
        "action_type": "hook_rewrite",
        "target_section": "hook",
        "instruction": "Rewrite the hook to open with a strong immediate claim.",
        "critique_claim_id": claim_id,
        "reasoning": "Fallback: no critic claims available.",
    }
