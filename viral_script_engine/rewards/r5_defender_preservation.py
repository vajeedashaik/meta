from dataclasses import dataclass
from typing import List

from viral_script_engine.agents.defender import DefenderOutput


@dataclass
class DefenderPreservationResult:
    score: float
    max_similarity: float
    best_matching_sentence: str


def _sentence_split(text: str) -> List[str]:
    import re
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s for s in sentences if s.strip()]


class DefenderPreservationReward:
    _model = None
    _cache: dict = {}

    def _get_model(self):
        if DefenderPreservationReward._model is None:
            from sentence_transformers import SentenceTransformer
            DefenderPreservationReward._model = SentenceTransformer("all-MiniLM-L6-v2")
        return DefenderPreservationReward._model

    def _embed(self, text: str):
        import hashlib
        key = hashlib.sha256(text.encode()).hexdigest()
        if key not in DefenderPreservationReward._cache:
            DefenderPreservationReward._cache[key] = self._get_model().encode(
                text, convert_to_tensor=True
            )
        return DefenderPreservationReward._cache[key]

    def score(self, defender_output: DefenderOutput, rewritten_script: str) -> DefenderPreservationResult:
        from sentence_transformers.util import cos_sim

        quote_emb = self._embed(defender_output.core_strength_quote)
        sentences = _sentence_split(rewritten_script)

        if not sentences:
            return DefenderPreservationResult(score=0.0, max_similarity=0.0, best_matching_sentence="")

        sims = [(float(cos_sim(quote_emb, self._embed(s))[0][0]), s) for s in sentences]
        max_sim, best_sent = max(sims, key=lambda x: x[0])

        if max_sim >= 0.85:
            final_score = 1.0
        elif max_sim >= 0.65:
            final_score = max_sim
        else:
            final_score = 0.0

        return DefenderPreservationResult(
            score=final_score,
            max_similarity=max_sim,
            best_matching_sentence=best_sent,
        )
