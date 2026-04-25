import json
import re
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel


class ModerationFlag(BaseModel):
    category: str
    trigger_phrase: str
    position: str
    severity: str
    suggestion: str


class ModerationOutput(BaseModel):
    flags: List[ModerationFlag]
    is_safe: bool
    overall_risk: str
    total_flags: int


_CATEGORY_LABEL_MAP = {
    "hate_speech_patterns": "hate_speech",
    "misleading_health_claims": "misleading_health",
    "copyright_bait_phrases": "copyright_bait",
    "engagement_bait": "engagement_bait",
    "spam_signals": "spam",
    "platform_policy_violations": "policy_violation",
}

_SEVERITY_MAP = {
    "hate_speech_patterns": "high",
    "misleading_health_claims": "high",
    "copyright_bait_phrases": "medium",
    "engagement_bait": "low",
    "spam_signals": "medium",
    "platform_policy_violations": "high",
}

_SUGGESTIONS = {
    "hate_speech_patterns": "Remove or replace with respectful, inclusive language.",
    "misleading_health_claims": "Replace with evidence-based language; avoid absolute health guarantees.",
    "copyright_bait_phrases": "Remove references to free/leaked content to avoid DMCA flags.",
    "engagement_bait": "Replace with a genuine question or value-based CTA.",
    "spam_signals": "Remove external link bait; focus on in-app value delivery.",
    "platform_policy_violations": "Remove policy-violating claims; keep messaging compliant.",
}


def _split_script(script: str) -> Dict[str, str]:
    sentences = re.split(r'(?<=[.!?])\s+', script.strip())
    if len(sentences) <= 5:
        return {"hook": script, "body": "", "cta": ""}
    hook = " ".join(sentences[:3])
    cta = " ".join(sentences[-2:])
    body = " ".join(sentences[3:-2])
    return {"hook": hook, "body": body, "cta": cta}


class ModerationAgent:
    """
    Checks scripts for content that would get flagged or shadowbanned on Reels.
    Zero LLM calls — purely rule-based against shadowban_triggers.json.
    """

    def __init__(self, kb_path: str = "data/shadowban_triggers.json"):
        resolved = Path(kb_path)
        if not resolved.is_absolute():
            resolved = Path(__file__).parent.parent / kb_path
        with open(resolved) as f:
            self._kb: Dict[str, List[str]] = json.load(f)

    def check(self, script: str) -> ModerationOutput:
        sections = _split_script(script)
        flags: List[ModerationFlag] = []

        for category, triggers in self._kb.items():
            severity = _SEVERITY_MAP.get(category, "low")
            label = _CATEGORY_LABEL_MAP.get(category, category)
            suggestion = _SUGGESTIONS.get(category, "Review and revise this content.")
            for position, text in sections.items():
                if not text:
                    continue
                text_lower = text.lower()
                for trigger in triggers:
                    if trigger in text_lower:
                        flags.append(ModerationFlag(
                            category=label,
                            trigger_phrase=trigger,
                            position=position,
                            severity=severity,
                            suggestion=suggestion,
                        ))

        has_high = any(f.severity == "high" for f in flags)
        has_medium = any(f.severity == "medium" for f in flags)

        if has_high:
            overall_risk = "high_risk"
        elif has_medium:
            overall_risk = "medium_risk"
        elif flags:
            overall_risk = "low_risk"
        else:
            overall_risk = "safe"

        return ModerationOutput(
            flags=flags,
            is_safe=not has_high,
            overall_risk=overall_risk,
            total_flags=len(flags),
        )
