"""Адаптери в пам'яті для демо і тестів.

BM25Index — справжній алгоритм BM25 (у проді його роль виконує повнотекстовий пошук PostgreSQL
з українським словником). HashingEmbedding і OverlapReranker — ЗАГЛУШКИ замість моделей
(multilingual-e5-large і bge-reranker-v2-m3): вони потрібні, щоб перевірити оркестрацію,
а не якість пошуку. ScriptedLLM і TemplateLLM — два різні «провайдери» LLM для перевірки,
що use case не змінюється при заміні адаптера.
"""
from __future__ import annotations

import itertools
import math
import re
import zlib
from collections import Counter

from rag.domain import Chunk, EscalationRequest, Prompt, Scored, Turn

TOKEN = re.compile(r"err_\d{4}|/[\w/{}.-]+|[^\W\d_][\w']*|\d{3,}")
STOP = {"через", "для", "при", "що", "як", "або", "після", "щоб", "який", "яка", "яке", "які", "від",
        "але", "чи", "мене", "мені", "вже", "ще", "там", "тут", "коли", "можна", "його", "їх", "без",
        "цей", "ця", "це", "ці", "так", "лише", "усі", "всі", "раз", "хочу", "пише", "мій", "наш"}


def tokenize(text: str) -> list[str]:
    """Коди помилок, шляхи API й числа від 3 цифр — одним токеном; слова без стоп-слів —
    грубою основою (перші 6 літер). У проді — український словник повнотекстового пошуку."""
    out = []
    for tok in TOKEN.findall(text.lower()):
        if tok.startswith(("err_", "/")) or tok.isdigit():
            out.append(tok)
        elif len(tok) > 2 and tok not in STOP:
            out.append(tok[:6])
    return out


def _visible(chunk: Chunk, tenant_id: str) -> bool:
    owner = chunk.meta.get("tenant_id")
    return owner is None or owner == tenant_id


class BM25Index:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks, self.k1, self.b = chunks, k1, b
        self._tf = [Counter(tokenize(c.text)) for c in chunks]
        self._len = [sum(tf.values()) for tf in self._tf]
        self._avg = sum(self._len) / len(self._len)
        df = Counter(t for tf in self._tf for t in tf)
        n = len(chunks)
        self._idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int, tenant_id: str) -> list[Scored]:
        q = tokenize(query)
        results = []
        for chunk, tf, length in zip(self.chunks, self._tf, self._len):
            if not _visible(chunk, tenant_id):
                continue
            score = 0.0
            for t in q:
                if t in tf:
                    f = tf[t]
                    score += self._idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * length / self._avg))
            if score > 0:
                results.append(Scored(chunk, score))
        return sorted(results, key=lambda s: s.score, reverse=True)[:k]


class HashingEmbedding:
    """ЗАГЛУШКА: хешований мішок слів, нормований. Не розуміє синонімів — лише для тестів."""

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim
        self.calls = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        vectors = []
        for text in texts:
            v = [0.0] * self.dim
            for tok in tokenize(text):
                v[zlib.crc32(tok.encode()) % self.dim] += 1.0
            norm = math.sqrt(sum(x * x for x in v)) or 1.0
            vectors.append([x / norm for x in v])
        return vectors


class InMemoryVectorStore:
    def __init__(self, chunks: list[Chunk], embedder: HashingEmbedding) -> None:
        self.chunks = chunks
        self._vectors = embedder.embed([c.text for c in chunks])

    def search(self, vector: list[float], k: int, tenant_id: str) -> list[Scored]:
        scored = [Scored(c, sum(a * b for a, b in zip(vector, v)))
                  for c, v in zip(self.chunks, self._vectors) if _visible(c, tenant_id)]
        return sorted(scored, key=lambda s: s.score, reverse=True)[:k]


class OverlapReranker:
    """ЗАГЛУШКА крос-енкодера: частка токенів питання, що є у фрагменті (0..1).
    Збіг коду помилки важить утричі більше, як і в навченому re-ranker'і на тікетах."""

    def rerank(self, query: str, candidates: list[Scored]) -> list[Scored]:
        q = set(tokenize(query))
        weight = {t: (3.0 if t.startswith("err_") else 1.0) for t in q}
        total = sum(weight.values()) or 1.0
        scored = [Scored(s.chunk, sum(weight[t] for t in q & set(tokenize(s.chunk.text))) / total)
                  for s in candidates]
        return sorted(scored, key=lambda s: s.score, reverse=True)


def _first_sentence(block: str) -> str:
    body = block.split("\n", 1)[1] if "\n" in block else block
    lines = [ln for ln in body.splitlines() if ln.strip() and not ln.startswith(("Payroll API", "#"))]
    return " ".join(lines[1:3]) if len(lines) > 2 else " ".join(lines)


class ScriptedLLM:
    """Провайдер A (у проді — адаптер Anthropic Messages API)."""

    name = "provider-A"

    def __init__(self) -> None:
        self.prompts: list[Prompt] = []

    def complete(self, prompt: Prompt) -> str:
        self.prompts.append(prompt)
        if not prompt.context_blocks:
            return "INSUFFICIENT_CONTEXT"
        return f"{_first_sentence(prompt.context_blocks[0])} [1]"

    def summarize(self, turns: list[Turn], max_tokens: int) -> str:
        users = [t.text for t in turns if t.role == "user"]
        text = "Раніше клієнт питав: " + "; ".join(users)
        return text[: max_tokens * 3]


class TemplateLLM(ScriptedLLM):
    """Провайдер B з іншим форматом відповіді (у проді — адаптер OpenAI / Azure OpenAI)."""

    name = "provider-B"

    def complete(self, prompt: Prompt) -> str:
        self.prompts.append(prompt)
        if not prompt.context_blocks:
            return "INSUFFICIENT_CONTEXT"
        return f"Коротко: {_first_sentence(prompt.context_blocks[0])}\nДжерело: [1]"


class InMemoryEscalation:
    def __init__(self) -> None:
        self.requests: list[EscalationRequest] = []
        self._ids = itertools.count(1)

    def create_ticket(self, request: EscalationRequest) -> str:
        self.requests.append(request)
        return f"SUP-{next(self._ids):04d}"
