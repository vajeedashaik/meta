import json
import re
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from viral_script_engine.platforms.platform_spec import PlatformRegistry

_FILLER_PHRASES = [
    "hey guys", "welcome back", "today i want to", "so today",
    "in this video", "what's up everyone", "hey everyone",
    "guys today", "hello everyone", "so basically", "you know",
    "kind of", "sort of", "basically", "um ", "uh ",
]

_COMMON_WORDS = {
    'i', 'the', 'a', 'an', 'my', 'your', 'its', 'it', 'is', 'are',
    'was', 'were', 'be', 'been', "i've", "i'm", "it's", "here's",
    'today', 'and', 'but', 'so', 'that', 'this', 'these', 'those',
    'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
    'or', 'not', 'you', 'we', 'they', 'he', 'she', 'if', 'do',
    'get', 'just', 'up', 'out', 'about', 'what', 'all', 'some',
}

_PROMISE_PATTERNS = [
    r'\d',
    r'\bhow to\b',
    r'\bwhy\b',
    r'\bwhat happens when\b',
    r'\bi made\b',
    r'\bwill\b',
    r'\bguaranteed\b',
    r'\bstep\b',
    r'\btips?\b',
    r'\bsecrets?\b',
    r'\bprove[sd]?\b',
    r'\bhere\'?s\b',
]

_KNOWN_PLATFORMS = ["Reels", "Shorts", "Feed", "TikTok"]


class ScriptFeatures(BaseModel):
    # Hook features (predicts early drop-off 0–5s)
    hook_word_count: int
    hook_has_number: bool
    hook_has_question: bool
    hook_has_promise: bool
    hook_filler_score: float        # 0=no filler, 1=all filler

    # Pacing features (predicts mid-video retention 5–30s)
    avg_words_per_sentence: float
    sentence_count: int
    short_sentence_ratio: float     # sentences < 8 words / total sentences
    section_balance_score: float    # how evenly hook:body:cta matches platform spec

    # Content features (predicts late retention 30s+)
    specificity_score: float        # ratio of specific nouns/numbers to total words
    cultural_ref_count: int
    cta_position_ratio: float       # word offset of CTA start / total words

    # Platform fit features
    platform: str
    word_count: int
    length_vs_optimal: float        # word_count / optimal_script_length for platform

    def to_vector(self) -> List[float]:
        platform_one_hot = [1.0 if self.platform == p else 0.0 for p in _KNOWN_PLATFORMS]
        return [
            float(self.hook_word_count),
            1.0 if self.hook_has_number else 0.0,
            1.0 if self.hook_has_question else 0.0,
            1.0 if self.hook_has_promise else 0.0,
            float(self.hook_filler_score),
            float(self.avg_words_per_sentence),
            float(self.sentence_count),
            float(self.short_sentence_ratio),
            float(self.section_balance_score),
            float(self.specificity_score),
            float(self.cultural_ref_count),
            float(self.cta_position_ratio),
            float(self.word_count),
            float(self.length_vs_optimal),
        ] + platform_one_hot


class FeatureExtractor:
    def __init__(self, cultural_kb_path: Optional[str] = None):
        self.platform_registry = PlatformRegistry()
        self._cultural_kb_path = cultural_kb_path
        self._cultural_kb: Optional[dict] = None

    def _load_kb(self) -> None:
        if self._cultural_kb is not None:
            return
        kb_path = self._cultural_kb_path or str(
            Path(__file__).parent.parent / "data" / "cultural_kb.json"
        )
        with open(kb_path, "r", encoding="utf-8") as f:
            self._cultural_kb = json.load(f)

    def extract(self, script: str, platform: str, region: str) -> ScriptFeatures:
        self._load_kb()
        spec = self.platform_registry.get(platform)
        sentences = [s for s in re.split(r'(?<=[.!?])\s+', script.strip()) if s.strip()]
        if not sentences:
            sentences = [script]
        total_words = len(script.split())

        # --- Hook: first ~20% of sentences (min 1, max 3) ---
        n = len(sentences)
        hook_end = max(1, min(3, int(n * 0.2))) if n >= 5 else max(1, min(2, n))
        hook_text = " ".join(sentences[:hook_end])
        hook_lower = hook_text.lower()
        hook_words = hook_text.split()

        hook_word_count = len(hook_words)
        hook_has_number = bool(re.search(r'\d', hook_text))
        hook_has_question = '?' in hook_text
        hook_has_promise = any(re.search(p, hook_lower) for p in _PROMISE_PATTERNS)

        filler_hits = sum(1 for phrase in _FILLER_PHRASES if phrase in hook_lower)
        hook_filler_score = min(1.0, filler_hits / max(hook_word_count, 1) * 4)

        # --- Pacing ---
        sentence_count = n
        words_per_sent = [len(s.split()) for s in sentences]
        avg_words_per_sentence = sum(words_per_sent) / max(n, 1)
        short_sentence_ratio = sum(1 for w in words_per_sent if w < 8) / max(n, 1)

        # Section balance: compare actual word distribution to platform spec
        cta_start_idx = max(hook_end + 1, n - max(1, int(n * 0.1)))
        hook_w = sum(len(s.split()) for s in sentences[:hook_end])
        body_w = sum(len(s.split()) for s in sentences[hook_end:cta_start_idx])
        cta_w = sum(len(s.split()) for s in sentences[cta_start_idx:])
        total_w = max(hook_w + body_w + cta_w, 1)

        opt = spec.optimal_sentences_per_section
        opt_total = max(sum(opt.values()), 1)
        opt_hook_r = opt.get("hook", 2) / opt_total
        opt_body_r = opt.get("body", 6) / opt_total
        act_hook_r = hook_w / total_w
        act_body_r = body_w / total_w
        balance_dev = (abs(act_hook_r - opt_hook_r) + abs(act_body_r - opt_body_r)) / 2
        section_balance_score = max(0.0, 1.0 - balance_dev * 4)

        # --- Content features ---
        words = script.split()
        specific_count = sum(
            1 for w in words
            if (
                re.search(r'\d', w)
                or (len(w) > 1 and w[0].isupper() and w.lower().strip('.,!?;:\'"') not in _COMMON_WORDS)
            )
        )
        specificity_score = min(1.0, specific_count / max(total_words, 1))

        cultural_ref_count = 0
        if self._cultural_kb and region in self._cultural_kb:
            kb = self._cultural_kb[region]
            script_lower = script.lower()
            cultural_ref_count = (
                sum(1 for r in kb.get("valid_refs", []) if r.lower() in script_lower)
                + sum(1 for i in kb.get("correct_idioms", []) if i.lower() in script_lower)
            )

        cta_word_offset = hook_w + body_w
        cta_position_ratio = cta_word_offset / max(total_words, 1)

        # --- Platform fit ---
        length_vs_optimal = total_words / max(spec.optimal_script_length_words, 1)

        return ScriptFeatures(
            hook_word_count=hook_word_count,
            hook_has_number=hook_has_number,
            hook_has_question=hook_has_question,
            hook_has_promise=hook_has_promise,
            hook_filler_score=round(hook_filler_score, 4),
            avg_words_per_sentence=round(avg_words_per_sentence, 4),
            sentence_count=sentence_count,
            short_sentence_ratio=round(short_sentence_ratio, 4),
            section_balance_score=round(section_balance_score, 4),
            specificity_score=round(specificity_score, 4),
            cultural_ref_count=cultural_ref_count,
            cta_position_ratio=round(cta_position_ratio, 4),
            platform=platform,
            word_count=total_words,
            length_vs_optimal=round(length_vs_optimal, 4),
        )
