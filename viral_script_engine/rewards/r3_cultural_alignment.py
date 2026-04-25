from dataclasses import dataclass
from typing import List
import json
import re


@dataclass
class CulturalRewardResult:
    score: float
    valid_refs_found: List[str]
    correct_idioms_found: List[str]
    invalid_signals_found: List[str]
    anachronistic_signals_found: List[str]
    region: str


class CulturalAlignmentReward:
    def __init__(self, knowledge_base_path: str = "data/cultural_kb.json"):
        with open(knowledge_base_path, "r", encoding="utf-8") as f:
            self._kb = json.load(f)

    def score(self, script: str, region: str) -> CulturalRewardResult:
        if region not in self._kb:
            return CulturalRewardResult(
                score=0.5,
                valid_refs_found=[],
                correct_idioms_found=[],
                invalid_signals_found=[],
                anachronistic_signals_found=[],
                region=region,
            )

        kb = self._kb[region]
        script_lower = script.lower()

        valid_refs_found = [r for r in kb["valid_refs"] if r.lower() in script_lower]
        correct_idioms_found = [i for i in kb["correct_idioms"] if i.lower() in script_lower]
        invalid_signals_found = [s for s in kb["invalid_signals"] if s.lower() in script_lower]
        anachronistic_signals_found = [a for a in kb["anachronistic_signals"] if a.lower() in script_lower]

        numerator = (
            len(valid_refs_found)
            + len(correct_idioms_found)
            - len(invalid_signals_found)
            - len(anachronistic_signals_found)
        )
        denominator = max(len(kb["valid_refs"]) + len(kb["correct_idioms"]), 1)
        raw_score = numerator / denominator
        clipped_score = max(0.0, min(1.0, raw_score))

        return CulturalRewardResult(
            score=clipped_score,
            valid_refs_found=valid_refs_found,
            correct_idioms_found=correct_idioms_found,
            invalid_signals_found=invalid_signals_found,
            anachronistic_signals_found=anachronistic_signals_found,
            region=region,
        )
