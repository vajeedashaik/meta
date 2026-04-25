import re
from dataclasses import dataclass, field
from typing import Dict

from viral_script_engine.rewards.base import BaseReward

_DEAD_OPENERS = [
    "hey guys", "welcome back", "today i want to", "so today",
    "in this video", "what's up everyone", "hey everyone",
    "guys today", "hello everyone", "so basically",
]

_COMMON_WORDS = {
    'i', 'the', 'a', 'an', 'my', 'your', 'its', 'it', 'is', 'are',
    'was', 'were', 'be', 'been', "i've", "i'm", "it's", "here's",
    'today', 'and', 'but', 'so', 'that', 'this', 'these', 'those',
}


@dataclass
class HookRewardResult:
    score: float
    checks_passed: int
    check_details: Dict[str, bool] = field(default_factory=dict)


def _extract_hook(text: str) -> str:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    hook = " ".join(sentences[:3]) if len(sentences) >= 3 else text
    words = hook.split()
    return " ".join(words[:50]) if len(words) > 50 else hook


class HookStrengthReward(BaseReward):
    def score(self, script: str) -> HookRewardResult:
        hook = _extract_hook(script)
        hook_lower = hook.lower()
        first_sentence = re.split(r'(?<=[.!?])\s+', hook.strip())[0].lower()

        checks = {
            "promise": self._check_promise(hook_lower),
            "curiosity": self._check_curiosity(hook_lower),
            "specificity": self._check_specificity(hook),
            "front_load": self._check_front_load(first_sentence),
            "anti_filler": self._check_anti_filler(hook_lower),
        }
        passed = sum(checks.values())
        return HookRewardResult(
            score=min(1.0, max(0.0, passed / 5)),
            checks_passed=passed,
            check_details=checks,
        )

    def _check_promise(self, hook: str) -> bool:
        bad = ["hey guys", "welcome back", "today we're talking about"]
        if any(b in hook for b in bad):
            return False
        patterns = [
            r'\d',
            r'\bhow to\b',
            r'\bwhy\b',
            r'\bwhat happens when\b',
            r'\bi made\b',
        ]
        return any(re.search(p, hook) for p in patterns)

    def _check_curiosity(self, hook: str) -> bool:
        patterns = [
            r'\?',
            r"but here'?s the thing",
            r"most \w+ don'?t know",
            r"the secret is",
            r"nobody tells you",
            r"most people don'?t",
        ]
        if not any(re.search(p, hook) for p in patterns):
            return False
        first = re.split(r'(?<=[.!?])\s+', hook)[0]
        if re.search(r'\?', first) and re.search(r'\b(is|are|was|were|means|equals)\b', first):
            return False
        return True

    def _check_specificity(self, hook: str) -> bool:
        if re.search(r'\d', hook):
            return True
        sentences = re.split(r'(?<=[.!?])\s+', hook)
        for sentence in sentences:
            words = sentence.split()[1:]
            for w in words:
                clean = w.strip('.,!?;:\'"')
                if clean and clean[0].isupper() and clean.lower() not in _COMMON_WORDS:
                    return True
        return False

    def _check_front_load(self, first_sentence: str) -> bool:
        signals = 0
        if re.search(r'\d', first_sentence):
            signals += 1
        promise_patterns = [r'\bhow to\b', r'\bwhy\b', r'\bwhat happens when\b', r'\bi made\b']
        if any(re.search(p, first_sentence) for p in promise_patterns):
            signals += 1
        if re.search(r'\?', first_sentence):
            signals += 1
        return signals >= 2

    def _check_anti_filler(self, hook: str) -> bool:
        return not any(hook.startswith(opener) for opener in _DEAD_OPENERS)
