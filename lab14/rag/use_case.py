"""Центральний use case: оркестрація RAG-запиту (Завдання 3 і 5)."""
from __future__ import annotations

import re

from rag.domain import Answer, ClientContext, EscalationRequest, Scored, Turn
from rag.fusion import rrf
from rag.ports import EmbeddingPort, EscalationPort, KeywordSearchPort, LLMPort, RerankerPort, VectorSearchPort
from rag.prompt import PromptBuilder

ERROR_CODE = re.compile(r"\bERR_\d{4}\b")
CITATION = re.compile(r"\[(\d+)\]")
# Теми, де бот не відповідає сам: гроші за тариф, юридичні спори, скарги.
ALWAYS_HUMAN = re.compile(r"поверн\w* кошт|скасува\w* підписк|скарг|юрист|\bсуд[а-яії]{0,3}\b|позов", re.IGNORECASE)
SOURCE_TRUST = {"api": 1.0, "help": 1.0, "policy": 1.0, "ticket": 0.8}
PAYROLL_URGENT = re.compile(r"зарплат|розрахун|виплат|аванс|ERR_409\d", re.IGNORECASE)


class AnswerSupportQuestion:
    def __init__(self, embedder: EmbeddingPort, vectors: VectorSearchPort, keywords: KeywordSearchPort,
                 reranker: RerankerPort, llm: LLMPort, escalation: EscalationPort,
                 prompt_builder: PromptBuilder | None = None,
                 low_confidence: float = 0.35, candidates: int = 30, rerank_top: int = 20, final_k: int = 5) -> None:
        self.embedder, self.vectors, self.keywords = embedder, vectors, keywords
        self.reranker, self.llm, self.escalation = reranker, llm, escalation
        self.prompts = prompt_builder or PromptBuilder(llm)
        self.low_confidence = low_confidence
        self.candidates, self.rerank_top, self.final_k = candidates, rerank_top, final_k

    def ask(self, ctx: ClientContext, question: str, history: list[Turn]) -> Answer:
        if ALWAYS_HUMAN.search(question):
            return self._escalate(ctx, question, history, [], "тема лише для оператора", 0.0)

        # 1. Embedding запиту і 2. гібридний пошук: dense + sparse, об'єднання RRF.
        vector = self.embedder.embed([question])[0]
        dense = self.vectors.search(vector, self.candidates, ctx.tenant_id)
        sparse = self.keywords.search(question, self.candidates, ctx.tenant_id)
        fused = rrf([dense, sparse])
        # 3. Точний код помилки з питання — фрагмент з цим кодом гарантовано серед кандидатів.
        codes = set(ERROR_CODE.findall(question))
        if codes:
            exact = [s for s in sparse if codes & set(s.chunk.meta.get("error_codes", []))]
            exact.sort(key=lambda s: s.chunk.source != "api")      # офіційна документація перед тікетами
            exact_ids = {s.chunk.id for s in exact}
            fused = exact + [s for s in fused if s.chunk.id not in exact_ids]
        # 4. Re-ranking крос-енкодером, скор 0..1 — він же міра впевненості.
        #    Тікетам довіряємо менше (×0.8): вони можуть бути застарілими чи про конкретного клієнта.
        reranked = self.reranker.rerank(question, fused[: self.rerank_top])
        reranked = [Scored(s.chunk, s.score * SOURCE_TRUST.get(s.chunk.source, 1.0)) for s in reranked]
        top = sorted(reranked, key=lambda s: s.score, reverse=True)[: self.final_k]
        confidence = top[0].score if top else 0.0
        if confidence < self.low_confidence:
            return self._escalate(ctx, question, history, top, "низька впевненість пошуку", confidence)

        # 5. Промпт з бюджетом токенів і 6. генерація.
        prompt = self.prompts.build(ctx, question, history, top)
        text = self.llm.complete(prompt)
        if "INSUFFICIENT_CONTEXT" in text:
            return self._escalate(ctx, question, history, top, "LLM: у контексті немає відповіді", confidence)
        cited = [int(n) for n in CITATION.findall(text)]
        if not cited or any(n < 1 or n > len(prompt.context_blocks) for n in cited):
            return self._escalate(ctx, question, history, top, "відповідь без коректних посилань",
                                  confidence, draft=text)
        citations = [top[n - 1].chunk.id for n in dict.fromkeys(cited)]
        return Answer(text, citations, confidence, prompt=prompt, retrieved=top)

    def _escalate(self, ctx: ClientContext, question: str, history: list[Turn], retrieved: list[Scored],
                  reason: str, confidence: float, draft: str | None = None) -> Answer:
        priority = "high" if PAYROLL_URGENT.search(question) or ctx.plan == "enterprise" else "normal"
        ticket = self.escalation.create_ticket(EscalationRequest(
            ctx.tenant_id, question, list(history) + [Turn("user", question)], retrieved, reason, priority, draft))
        text = ("Передаю ваше питання спеціалісту підтримки — він уже бачить історію розмови. "
                f"Номер звернення {ticket}.")
        return Answer(text, [], confidence, escalated=True, ticket_id=ticket, reason=reason, retrieved=retrieved)
