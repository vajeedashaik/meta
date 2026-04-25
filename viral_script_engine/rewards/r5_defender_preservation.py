import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from viral_script_engine.agents.defender import DefenderOutput


@dataclass
class DefenderPreservationResult:
    score: float
    max_similarity: float
    best_matching_sentence: str


def _sentence_split(text: str) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s for s in sentences if s.strip()]


def _tokenize(text: str) -> List[str]:
    return re.findall(r"\b\w+\b", text.lower())


def _tfidf_vector(tokens: List[str], vocab: Dict[str, int]) -> np.ndarray:
    vec = np.zeros(len(vocab), dtype=np.float32)
    for t in tokens:
        if t in vocab:
            vec[vocab[t]] += 1
    total = max(len(tokens), 1)
    return vec / total


def _cosine_np(a: np.ndarray, b: np.ndarray) -> float:
    n1 = np.linalg.norm(a)
    n2 = np.linalg.norm(b)
    if n1 == 0 or n2 == 0:
        return 0.0 if n1 != n2 else 1.0
    return float(np.dot(a, b) / (n1 * n2))


class DefenderPreservationReward:
    _st_model: Optional[object] = None
    _use_st: Optional[bool] = None
    _cache: dict = {}

    def _try_load_st(self) -> bool:
        if DefenderPreservationReward._use_st is not None:
            return DefenderPreservationReward._use_st
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401
            DefenderPreservationReward._st_model = SentenceTransformer("all-MiniLM-L6-v2")
            DefenderPreservationReward._use_st = True
        except Exception:
            DefenderPreservationReward._use_st = False
        return DefenderPreservationReward._use_st

    def _embed_st(self, text: str):
        import hashlib
        key = hashlib.sha256(text.encode()).hexdigest()
        if key not in DefenderPreservationReward._cache:
            DefenderPreservationReward._cache[key] = DefenderPreservationReward._st_model.encode(
                text, convert_to_tensor=True
            )
        return DefenderPreservationReward._cache[key]

    def _cosine_st(self, a, b) -> float:
        import torch
        import torch.nn.functional as F
        a = a.unsqueeze(0) if a.dim() == 1 else a
        b = b.unsqueeze(0) if b.dim() == 1 else b
        return float(F.cosine_similarity(a, b))

    def _similarity(self, text1: str, text2: str) -> float:
        if self._try_load_st():
            return self._cosine_st(self._embed_st(text1), self._embed_st(text2))
        t1 = _tokenize(text1)
        t2 = _tokenize(text2)
        vocab = {w: i for i, w in enumerate(set(t1 + t2))}
        return _cosine_np(_tfidf_vector(t1, vocab), _tfidf_vector(t2, vocab))

    def score(self, defender_output: DefenderOutput, rewritten_script: str) -> DefenderPreservationResult:
        quote = defender_output.core_strength_quote
        sentences = _sentence_split(rewritten_script)

        if not sentences:
            return DefenderPreservationResult(score=0.0, max_similarity=0.0, best_matching_sentence="")

        sims = [(self._similarity(quote, s), s) for s in sentences]
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
