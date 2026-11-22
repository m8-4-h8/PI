"""Завдання 4. Метрики якості."""
from __future__ import annotations

from datetime import datetime, timedelta


def recall_at_k(ranked_ids: list[str], relevant: set[str], k: int = 5) -> float:
    """Без LLM: частка релевантних фрагментів, що потрапили в top-k."""
    return len(set(ranked_ids[:k]) & relevant) / len(relevant) if relevant else 0.0


def mrr(results: list[tuple[list[str], set[str]]]) -> float:
    """Mean Reciprocal Rank: 1 / позиція першого релевантного, середнє по запитах."""
    total = 0.0
    for ranked, relevant in results:
        total += next((1 / i for i, cid in enumerate(ranked, start=1) if cid in relevant), 0.0)
    return total / len(results) if results else 0.0


def context_precision(relevance: list[bool]) -> float:
    """RAGAS Context Precision: середнє precision@k по позиціях релевантних фрагментів.
    relevance[i] — чи релевантний i-й фрагмент (у RAGAS це вирішує LLM-суддя)."""
    hits, score = 0, 0.0
    for k, rel in enumerate(relevance, start=1):
        if rel:
            hits += 1
            score += hits / k
    return score / hits if hits else 0.0


def faithfulness(claim_supported: list[bool]) -> float:
    """RAGAS Faithfulness: частка тверджень відповіді, які підтверджує контекст.
    Розбиття на твердження і перевірку кожного робить LLM-суддя; тут — уже готові вердикти."""
    return sum(claim_supported) / len(claim_supported) if claim_supported else 0.0


def resolution_rate(conversations: list[dict], tickets: list[dict], window_hours: int = 72) -> float:
    """Без LLM: частка розмов, які бот закрив сам, і той самий користувач не створив тікет
    на ту саму тему протягом window_hours."""
    window = timedelta(hours=window_hours)
    resolved = 0
    for conv in conversations:
        if conv["escalated"]:
            continue
        end = datetime.fromisoformat(conv["ended_at"])
        came_back = any(t["user"] == conv["user"] and t["topic"] == conv["topic"]
                        and end <= datetime.fromisoformat(t["created_at"]) <= end + window for t in tickets)
        resolved += not came_back
    return resolved / len(conversations) if conversations else 0.0
