"""Reciprocal Rank Fusion: об'єднання dense і sparse без калібрування шкал скорів."""
from __future__ import annotations

from rag.domain import Scored

RRF_K = 60


def rrf(rankings: list[list[Scored]], k: int = RRF_K) -> list[Scored]:
    scores: dict[str, float] = {}
    chunks = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item.chunk.id] = scores.get(item.chunk.id, 0.0) + 1.0 / (k + rank)
            chunks[item.chunk.id] = item.chunk
    ordered = sorted(scores, key=lambda cid: scores[cid], reverse=True)
    return [Scored(chunks[cid], scores[cid]) for cid in ordered]
