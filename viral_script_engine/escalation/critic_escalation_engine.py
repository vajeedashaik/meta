import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from viral_script_engine.agents.llm_backend import LLMBackend
from viral_script_engine.escalation.difficulty_tracker import DifficultyTracker

_SYSTEM_PROMPT_TEMPLATE = """You are designing training challenges for an RL agent learning to improve video scripts.
The agent has mastered detecting and fixing '{mastered_class}' flaws.

Generate a harder challenge:
1. Create a script with a '{mastered_class}' flaw that is MORE SUBTLE than the example
2. Add a CONFLICTING CONSTRAINT: fixing the '{mastered_class}' flaw should create or
   worsen a different flaw from: {other_classes}
3. Difficulty: HARD — agent must learn action ordering, not just action selection

A challenge is good when: fixing the obvious flaw first leads to WORSE total reward
than fixing a less obvious flaw first.

Return JSON only:
{{
  "script_text": "...",
  "dominant_flaw": "...",
  "conflicting_flaw": "...",
  "why_its_harder": "one sentence",
  "optimal_action_order": ["action1", "action2"],
  "trap_action": "action that looks correct but degrades total reward"
}}"""

_USER_PROMPT_TEMPLATE = """MASTERED CLASS: {mastered_class}
REGION: {region}
PLATFORM: {platform}

ORIGINAL SCRIPT EXAMPLE (already mastered at this difficulty):
{original_script_example}

Generate a HARDER escalated challenge where fixing the dominant flaw immediately is a trap.
Respond with JSON only."""


@dataclass
class EscalatedChallenge:
    source_class: str
    script_text: str
    region: str
    platform: str
    dominant_flaw: str
    conflicting_flaw: str
    why_its_harder: str
    optimal_action_order: List[str]
    trap_action: str
    difficulty_level: str = "self_generated"
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    def to_script_dict(self) -> dict:
        return {
            "script_id": f"escalated_{self.source_class}_{self.generated_at[:10]}",
            "script_text": self.script_text,
            "region": self.region,
            "platform": self.platform,
            "niche": "escalated",
            "difficulty": "self_generated",
        }


class CriticEscalationEngine:
    def __init__(self, backend: str = "anthropic", model_name: str = "claude-haiku-4-5-20251001"):
        self.llm = LLMBackend(backend=backend, model_name=model_name)
        self.escalated_classes: Dict[str, List[EscalatedChallenge]] = {}

    @staticmethod
    def _extract_json(text: str) -> dict:
        import re
        text = text.strip()
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        start = text.find("{")
        if start != -1:
            depth, in_str, esc = 0, False, False
            for i, c in enumerate(text[start:], start):
                if esc:
                    esc = False
                    continue
                if c == "\\" and in_str:
                    esc = True
                    continue
                if c == '"':
                    in_str = not in_str
                elif not in_str:
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            try:
                                return json.loads(text[start: i + 1])
                            except json.JSONDecodeError:
                                break
        raise ValueError(f"No valid JSON in escalation response: {text[:300]}")

    def escalate(
        self,
        mastered_class: str,
        original_script_example: str,
        region: str,
        platform: str,
    ) -> EscalatedChallenge:
        other_classes = [c for c in DifficultyTracker.CRITIQUE_CLASSES if c != mastered_class]
        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            mastered_class=mastered_class,
            other_classes=", ".join(other_classes),
        )
        user_prompt = _USER_PROMPT_TEMPLATE.format(
            mastered_class=mastered_class,
            region=region,
            platform=platform,
            original_script_example=original_script_example,
        )

        raw = self.llm.generate(system_prompt, user_prompt, max_tokens=1024)
        data = self._extract_json(raw)

        challenge = EscalatedChallenge(
            source_class=mastered_class,
            script_text=data["script_text"],
            region=region,
            platform=platform,
            dominant_flaw=data["dominant_flaw"],
            conflicting_flaw=data["conflicting_flaw"],
            why_its_harder=data["why_its_harder"],
            optimal_action_order=data.get("optimal_action_order", []),
            trap_action=data.get("trap_action", ""),
        )

        self.escalated_classes.setdefault(mastered_class, []).append(challenge)
        return challenge

    def get_next_challenge(self, difficulty_tracker: DifficultyTracker) -> Optional[EscalatedChallenge]:
        mastered = difficulty_tracker.get_mastered_classes()
        if not mastered:
            return None

        for cls in mastered:
            challenges = self.escalated_classes.get(cls, [])
            if challenges:
                return challenges[-1]

        return None

    def total_generated(self) -> int:
        return sum(len(v) for v in self.escalated_classes.values())
