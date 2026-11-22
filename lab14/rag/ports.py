"""Порти (Hexagonal Architecture, Лаба 3). Use case знає лише ці інтерфейси."""
from __future__ import annotations

from typing import Protocol

from rag.domain import ClientContext, EscalationRequest, Prompt, Scored, Turn


# --- Primary port: звідки приходить запит клієнта (веб-віджет, Slack, email) ---
class SupportChatPort(Protocol):
    def ask(self, ctx: ClientContext, question: str, history: list[Turn]): ...


# --- Secondary ports: що потрібно use case від зовнішнього світу ---
class EmbeddingPort(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class VectorSearchPort(Protocol):
    def search(self, vector: list[float], k: int, tenant_id: str) -> list[Scored]: ...


class KeywordSearchPort(Protocol):
    def search(self, query: str, k: int, tenant_id: str) -> list[Scored]: ...


class RerankerPort(Protocol):
    def rerank(self, query: str, candidates: list[Scored]) -> list[Scored]: ...


class LLMPort(Protocol):
    def complete(self, prompt: Prompt) -> str: ...

    def summarize(self, turns: list[Turn], max_tokens: int) -> str: ...


class EscalationPort(Protocol):
    def create_ticket(self, request: EscalationRequest) -> str: ...
