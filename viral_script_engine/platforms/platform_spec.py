from pathlib import Path
from typing import Dict
import json

from pydantic import BaseModel

_DEFAULT_KB = str(Path(__file__).parent / "platform_kb.json")


class PlatformSpec(BaseModel):
    platform: str
    hook_window_seconds: int
    optimal_script_length_words: int
    max_script_length_words: int
    hook_length_words: int
    cta_position: str
    optimal_sentences_per_section: Dict[str, int]
    pacing_norm: str
    penalty_for_slow_start: bool
    reward_for_pattern_interrupt: bool


class PlatformRegistry:
    """Single source of truth for all platform-specific reward thresholds."""

    def __init__(self, kb_path: str = _DEFAULT_KB):
        with open(kb_path) as f:
            raw = json.load(f)
        self.specs = {k: PlatformSpec(platform=k, **{
            kk: vv for kk, vv in v.items()
            if kk not in ("avg_retention_curve", "notes")
        }) for k, v in raw.items()}

    def get(self, platform: str) -> PlatformSpec:
        if platform not in self.specs:
            raise ValueError(
                f"Unknown platform: {platform!r}. Valid: {list(self.specs.keys())}"
            )
        return self.specs[platform]
