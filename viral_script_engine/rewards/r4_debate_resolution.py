from dataclasses import dataclass

from viral_script_engine.agents.critic import CriticAgent, CritiqueClaim
from viral_script_engine.environment.actions import ArbitratorAction


@dataclass
class DebateResolutionResult:
    score: float
    resolution_status: str
    original_claim_id: str
    original_claim_class: str
    new_claims_count: int


def _parse_seconds(ts: str) -> float:
    if not ts or ts == "N/A":
        return -1.0
    try:
        start = ts.split("-")[0].strip()
        parts = start.split(":")
        return float(parts[0]) * 60 + float(parts[1])
    except Exception:
        return -1.0


class DebateResolutionReward:
    def __init__(self, critic_agent: CriticAgent):
        self.critic = critic_agent

    def score(
        self,
        new_script: str,
        original_action: ArbitratorAction,
        original_claim: CritiqueClaim,
        region: str,
        platform: str,
        niche: str,
    ) -> DebateResolutionResult:
        new_critique = self.critic.critique(new_script, region, platform, niche)
        new_claims = new_critique.claims

        orig_ts = _parse_seconds(original_claim.timestamp_range)
        orig_class = original_claim.critique_class

        matching = []
        for c in new_claims:
            if c.critique_class != orig_class:
                continue
            if orig_ts == -1.0:
                matching.append(c)
            else:
                new_ts = _parse_seconds(c.timestamp_range)
                if new_ts != -1.0 and abs(new_ts - orig_ts) <= 5:
                    matching.append(c)

        if not matching:
            return DebateResolutionResult(
                score=1.0,
                resolution_status="resolved",
                original_claim_id=original_claim.claim_id,
                original_claim_class=orig_class,
                new_claims_count=len(new_claims),
            )

        worst = max(matching, key=lambda c: {"high": 2, "medium": 1, "low": 0}.get(c.severity, 1))
        if worst.severity == "low":
            return DebateResolutionResult(
                score=0.5,
                resolution_status="partially_resolved",
                original_claim_id=original_claim.claim_id,
                original_claim_class=orig_class,
                new_claims_count=len(new_claims),
            )

        return DebateResolutionResult(
            score=0.0,
            resolution_status="persists",
            original_claim_id=original_claim.claim_id,
            original_claim_class=orig_class,
            new_claims_count=len(new_claims),
        )
