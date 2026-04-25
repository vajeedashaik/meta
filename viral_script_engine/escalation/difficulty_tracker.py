import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


@dataclass
class CritiqueClassRecord:
    critique_class: str
    total_episodes: int = 0
    resolved_episodes: int = 0
    consecutive_resolutions: int = 0
    mastery_threshold: int = 3
    is_mastered: bool = False
    avg_r4_score: float = 0.0
    last_10_r4_scores: List[float] = field(default_factory=list)


class DifficultyTracker:
    CRITIQUE_CLASSES = [
        "hook_weakness",
        "pacing_issue",
        "cultural_mismatch",
        "cta_buried",
        "coherence_break",
        "retention_risk",
    ]

    def __init__(self, persistence_path: str = "logs/difficulty_tracker.json"):
        self.persistence_path = persistence_path
        self.records: Dict[str, CritiqueClassRecord] = {
            cls: CritiqueClassRecord(critique_class=cls) for cls in self.CRITIQUE_CLASSES
        }
        self._load()

    def _load(self):
        if os.path.exists(self.persistence_path):
            try:
                with open(self.persistence_path, encoding="utf-8") as f:
                    data = json.load(f)
                for cls, rec_data in data.get("records", {}).items():
                    if cls in self.records:
                        r = self.records[cls]
                        r.total_episodes = rec_data.get("total_episodes", 0)
                        r.resolved_episodes = rec_data.get("resolved_episodes", 0)
                        r.consecutive_resolutions = rec_data.get("consecutive_resolutions", 0)
                        r.is_mastered = rec_data.get("is_mastered", False)
                        r.avg_r4_score = rec_data.get("avg_r4_score", 0.0)
                        r.last_10_r4_scores = rec_data.get("last_10_r4_scores", [])
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        os.makedirs(os.path.dirname(self.persistence_path) if os.path.dirname(self.persistence_path) else ".", exist_ok=True)
        payload = {
            "records": {cls: asdict(rec) for cls, rec in self.records.items()}
        }
        with open(self.persistence_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def record_episode(self, dominant_critique_class: str, r4_score: float, episode_id: str):
        if dominant_critique_class not in self.records:
            dominant_critique_class = "hook_weakness"

        rec = self.records[dominant_critique_class]
        rec.total_episodes += 1

        rec.last_10_r4_scores.append(r4_score)
        if len(rec.last_10_r4_scores) > 10:
            rec.last_10_r4_scores.pop(0)
        rec.avg_r4_score = sum(rec.last_10_r4_scores) / len(rec.last_10_r4_scores)

        resolved = r4_score >= 0.8
        if resolved:
            rec.resolved_episodes += 1
            rec.consecutive_resolutions += 1
        else:
            rec.consecutive_resolutions = 0
            rec.is_mastered = False

        if rec.consecutive_resolutions >= rec.mastery_threshold:
            rec.is_mastered = True

        self._save()

    def get_next_difficulty_class(self) -> str:
        mastered = self.get_mastered_classes()
        if mastered:
            return mastered[0]

        eligible = [
            cls for cls, rec in self.records.items()
            if rec.total_episodes >= 3 and not rec.is_mastered
        ]
        if eligible:
            return min(eligible, key=lambda c: self.records[c].avg_r4_score)

        return "hook_weakness"

    def get_mastered_classes(self) -> List[str]:
        return [cls for cls, rec in self.records.items() if rec.is_mastered]

    def get_hardest_unsolved_class(self) -> str:
        candidates = [
            (cls, rec) for cls, rec in self.records.items()
            if not rec.is_mastered and rec.total_episodes > 0
        ]
        if not candidates:
            return "hook_weakness"
        return min(candidates, key=lambda x: x[1].avg_r4_score)[0]

    def summary(self) -> dict:
        return {
            "mastered_classes": self.get_mastered_classes(),
            "hardest_unsolved": self.get_hardest_unsolved_class(),
            "records": {
                cls: {
                    "total_episodes": rec.total_episodes,
                    "resolved_episodes": rec.resolved_episodes,
                    "consecutive_resolutions": rec.consecutive_resolutions,
                    "is_mastered": rec.is_mastered,
                    "avg_r4_score": round(rec.avg_r4_score, 4),
                }
                for cls, rec in self.records.items()
            },
        }
