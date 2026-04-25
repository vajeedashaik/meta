import hashlib
import re
from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np

from viral_script_engine.rewards.base import BaseReward


@dataclass
class CoherenceRewardResult:
    score: float
    raw_similarity: float
    interpretation: str


def _tokenize(text: str):
    return re.findall(r"\b\w+\b", text.lower())


def _tfidf_vector(tokens: list, vocab: Dict[str, int]) -> np.ndarray:
    vec = np.zeros(len(vocab), dtype=np.float32)
    for t in tokens:
        if t in vocab:
            vec[vocab[t]] += 1
    total = max(len(tokens), 1)
    return vec / total


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    n1 = np.linalg.norm(a)
    n2 = np.linalg.norm(b)
    if n1 == 0 or n2 == 0:
        return 0.0 if n1 != n2 else 1.0
    return float(np.dot(a, b) / (n1 * n2))


class CoherenceReward(BaseReward):
    _cache: dict = {}

    def __init__(self):
        self._st_model: Optional[object] = None
        self._use_st: Optional[bool] = None

    def _try_load_st(self) -> bool:
        if self._use_st is not None:
            return self._use_st
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401
            self._st_model = SentenceTransformer("all-MiniLM-L6-v2")
            self._use_st = True
        except Exception:
            self._use_st = False
        return self._use_st

    def _embed_st(self, text: str) -> "torch.Tensor":
        key = hashlib.sha256(text.encode()).hexdigest()
        if key not in self._cache:
            self._cache[key] = self._st_model.encode(text, convert_to_tensor=True)
        return self._cache[key]

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
        return _cosine(_tfidf_vector(t1, vocab), _tfidf_vector(t2, vocab))

    def score(self, original: str, rewritten: str) -> CoherenceRewardResult:
        sim = self._similarity(original, rewritten)
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
