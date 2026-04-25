import hashlib
from dataclasses import dataclass

from viral_script_engine.rewards.base import BaseReward


@dataclass
class CoherenceRewardResult:
    score: float
    raw_similarity: float
    interpretation: str


class CoherenceReward(BaseReward):
    _cache: dict = {}

    def __init__(self):
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model

    def _embed(self, text: str):
        key = hashlib.sha256(text.encode()).hexdigest()
        if key not in self._cache:
            self._cache[key] = self._get_model().encode(text, convert_to_tensor=True)
        return self._cache[key]

    def _cosine_sim(self, a, b) -> float:
        from sentence_transformers.util import cos_sim
        return float(cos_sim(a, b)[0][0])

    def score(self, original: str, rewritten: str) -> CoherenceRewardResult:
        sim = self._cosine_sim(self._embed(original), self._embed(rewritten))
        if sim > 0.95:
            score, interpretation = 0.8, "barely_changed"
        elif sim >= 0.80:
            score = 0.5 + (sim - 0.80) / 0.15 * 0.5
            interpretation = "good_coherence"
        elif sim >= 0.65:
            score = (sim - 0.65) / 0.15 * 0.5
            interpretation = "moderate_drift"
        else:
            score, interpretation = 0.0, "drifted_too_far"
        return CoherenceRewardResult(score=score, raw_similarity=sim, interpretation=interpretation)
