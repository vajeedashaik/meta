import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel


class OriginalityFlag(BaseModel):
    template_type: str
    matched_pattern: str
    script_excerpt: str
    suggestion: str


class OriginalityOutput(BaseModel):
    flags: List[OriginalityFlag]
    originality_score: float
    is_generic: bool
    unique_elements: List[str]


_TEMPLATE_TYPE_MAP = {
    "overused_hooks": "overused_hook",
    "overused_structures": "overused_structure",
    "overused_cta_phrases": "overused_cta",
    "overused_transitions": "overused_transition",
}

_SUGGESTIONS = {
    "overused_hook": "Rewrite the hook with a specific data point, personal story, or unexpected angle.",
    "overused_structure": "Try an unconventional narrative arc — start mid-story or end with the question.",
    "overused_cta": "Replace with a specific, contextual call-to-action tied to the video's content.",
    "overused_transition": "Cut the transition filler and jump directly to the next point.",
}

_FUZZY_THRESHOLD = 0.75


def _split_script(script: str) -> Dict[str, str]:
    sentences = re.split(r'(?<=[.!?])\s+', script.strip())
    if len(sentences) <= 5:
        return {"hook": script, "body": "", "cta": ""}
    hook = " ".join(sentences[:3])
    cta = " ".join(sentences[-2:])
    body = " ".join(sentences[3:-2])
    return {"hook": hook, "body": body, "cta": cta}


def _fuzzy_match(text: str, pattern: str) -> bool:
    text_lower = text.lower()
    pattern_lower = pattern.lower()
    if pattern_lower in text_lower:
        return True
    ratio = SequenceMatcher(None, text_lower, pattern_lower).ratio()
    return ratio >= _FUZZY_THRESHOLD


class OriginalityAgent:
    """
    Measures how distinct the script sounds compared to overused Reels formats.
    Zero LLM calls — fuzzy string matching against viral_templates.json.
    Uses difflib.SequenceMatcher (threshold: 0.75 similarity).
    """

    def __init__(self, templates_path: str = "data/viral_templates.json"):
        resolved = Path(templates_path)
        if not resolved.is_absolute():
            resolved = Path(__file__).parent.parent / templates_path
        with open(resolved) as f:
            self._templates: Dict[str, List[str]] = json.load(f)

    def check(self, script: str) -> OriginalityOutput:
        sections = _split_script(script)
        flags: List[OriginalityFlag] = []
        matched_sections = set()

        for category, patterns in self._templates.items():
            template_type = _TEMPLATE_TYPE_MAP.get(category, category)
            suggestion = _SUGGESTIONS.get(template_type, "Make this section more original.")
            for pos, text in sections.items():
                if not text:
                    continue
                sentences = re.split(r'(?<=[.!?])\s+', text.strip())
                for sentence in sentences:
                    for pattern in patterns:
                        if _fuzzy_match(sentence, pattern):
                            section_key = f"{pos}:{sentence[:40]}"
                            matched_sections.add(section_key)
                            flags.append(OriginalityFlag(
                                template_type=template_type,
                                matched_pattern=pattern,
                                script_excerpt=sentence[:80],
                                suggestion=suggestion,
                            ))

        all_sentences = re.split(r'(?<=[.!?])\s+', script.strip())
        total = max(len(all_sentences), 1)
        matched_count = len(matched_sections)
        originality_score = max(0.0, min(1.0, 1.0 - (matched_count / total)))

        unique_elements = [
            s for s in all_sentences
            if not any(
                _fuzzy_match(s, pattern)
                for patterns in self._templates.values()
                for pattern in patterns
            )
        ]

        return OriginalityOutput(
            flags=flags,
            originality_score=originality_score,
            is_generic=originality_score < 0.4,
            unique_elements=unique_elements,
        )
