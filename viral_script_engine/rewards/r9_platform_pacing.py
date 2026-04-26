import re
from dataclasses import dataclass

from viral_script_engine.platforms.platform_spec import PlatformRegistry

_PACING_THRESHOLDS = {"very_fast": 8, "fast": 12, "moderate": 18}
_CTA_TARGETS = {
    "last_5_percent": 0.95,
    "last_8_percent": 0.92,
    "last_10_percent": 0.90,
    "last_15_percent": 0.85,
}


@dataclass
class PacingRewardResult:
    score: float
    pacing_score: float
    ratio_score: float
    cta_score: float
    platform: str


def _split_sections(script: str):
    """Split script into hook, body, cta by sentence position."""
    sentences = re.split(r'(?<=[.!?])\s+', script.strip())
    if not sentences:
        return "", "", ""
    n = len(sentences)
    if n == 1:
        return sentences[0], "", ""
    if n == 2:
        return sentences[0], sentences[1], ""
    # hook = first ~20%, body = next ~70%, cta = last ~10%
    hook_end = max(1, int(n * 0.2))
    cta_start = max(hook_end + 1, int(n * 0.9))
    hook = " ".join(sentences[:hook_end])
    body = " ".join(sentences[hook_end:cta_start])
    cta = " ".join(sentences[cta_start:])
    return hook, body, cta


def _avg_words_per_sentence(text: str) -> float:
    if not text.strip():
        return 0.0
    sentences = [s for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s]
    if not sentences:
        return 0.0
    total_words = sum(len(s.split()) for s in sentences)
    return total_words / len(sentences)


class PlatformPacingReward:
    """
    Rule-based pacing reward — zero LLM calls.
    Checks sentence length distribution, section ratios, and CTA position
    against the target platform's spec.
    """

    def __init__(self):
        self.platform_registry = PlatformRegistry()

    def score(self, script: str, platform: str) -> PacingRewardResult:
        spec = self.platform_registry.get(platform)
        hook, body, cta = _split_sections(script)

        # Check 1: avg words per sentence in hook vs pacing norm
        hook_avg_words = _avg_words_per_sentence(hook) if hook else 0.0
        threshold = _PACING_THRESHOLDS.get(spec.pacing_norm, 12)
        if hook_avg_words == 0.0:
            pacing_score = 0.5
        elif hook_avg_words <= threshold:
            pacing_score = 1.0
        else:
            pacing_score = max(0.0, 1.0 - (hook_avg_words - threshold) / threshold)

        # Check 2: section length ratio vs optimal
        hook_words = len(hook.split()) if hook else 0
        body_words = len(body.split()) if body else 0
        cta_words = len(cta.split()) if cta else 0
        total_words = max(hook_words + body_words + cta_words, 1)

        section_totals = sum(spec.optimal_sentences_per_section.values())
        optimal_hook_ratio = spec.optimal_sentences_per_section["hook"] / section_totals
        actual_hook_ratio = hook_words / total_words
        deviation = abs(actual_hook_ratio - optimal_hook_ratio)
        ratio_score = max(0.0, 1.0 - min(1.0, deviation / max(optimal_hook_ratio, 0.01)))

        # Check 3: CTA position
        cta_start_pos = (hook_words + body_words) / total_words
        cta_target = _CTA_TARGETS.get(spec.cta_position, 0.90)
        cta_score = 1.0 if cta_start_pos >= cta_target else 0.5

        final_score = pacing_score * 0.4 + ratio_score * 0.4 + cta_score * 0.2
        return PacingRewardResult(
            score=round(final_score, 4),
            pacing_score=round(pacing_score, 4),
            ratio_score=round(ratio_score, 4),
            cta_score=round(cta_score, 4),
            platform=platform,
        )
