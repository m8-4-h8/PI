"""Доменні об'єкти RAG-системи PeopleFlow. Не залежать від жодного провайдера."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    source: str                 # help | api | ticket | policy
    title: str
    meta: dict = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class Scored:
    chunk: Chunk
    score: float


@dataclass(frozen=True)
class Turn:
    role: str                   # user | assistant
    text: str


@dataclass(frozen=True)
class ClientContext:
    tenant_id: str
    plan: str                   # тариф визначає SLA ескалації
    role: str                   # payroll_admin, chief_accountant, hr, employee
    modules: tuple[str, ...] = ()


@dataclass
class Prompt:
    """Нейтральна до провайдера структура. Адаптер LLM перекладає її у свій формат."""

    system: str
    context_blocks: list[str]
    history_summary: str
    recent_turns: list[Turn]
    question: str
    tokens: int = 0
    dropped_chunks: int = 0
    sections: dict = field(default_factory=dict)


@dataclass
class Answer:
    text: str
    citations: list[str]
    confidence: float
    escalated: bool = False
    ticket_id: str | None = None
    reason: str = ""
    prompt: Prompt | None = None
    retrieved: list[Scored] = field(default_factory=list)


@dataclass(frozen=True)
class EscalationRequest:
    tenant_id: str
    question: str
    transcript: list[Turn]
    retrieved: list[Scored]
    reason: str
    priority: str
    draft_answer: str | None = None
