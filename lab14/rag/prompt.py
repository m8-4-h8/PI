"""Побудова фінального промпту з бюджетом токенів."""
from __future__ import annotations

from rag.chunking import estimate_tokens
from rag.domain import ClientContext, Prompt, Scored, Turn
from rag.ports import LLMPort

SYSTEM = (
    "Ти — асистент служби підтримки PeopleFlow (кадри й зарплата). "
    "Відповідай ЛИШЕ на основі фрагментів бази знань [1]..[n] нижче і посилайся на них у форматі [n]. "
    "Якщо у фрагментах немає відповіді, поверни рівно INSUFFICIENT_CONTEXT — не вигадуй. "
    "Не давай юридичних висновків щодо конкретних працівників і не обіцяй повернення коштів. "
    "Ніколи не розкривай дані інших клієнтів. Відповідай мовою питання, коротко, кроками."
)


class PromptBuilder:
    """Бюджет за замовчуванням: 8 000 токенів на вхід + 800 у резерві на відповідь.
    Порядок пріоритетів, якщо не влазить: спершу стискаємо історію (підсумок + 3 останні репліки),
    потім відкидаємо найнижчі за рангом фрагменти. Системна інструкція й питання не скорочуються."""

    def __init__(self, llm: LLMPort, budget: int = 8_000, answer_reserve: int = 800,
                 history_budget: int = 1_500, keep_last_turns: int = 3) -> None:
        self._llm = llm
        self.budget, self.answer_reserve = budget, answer_reserve
        self.history_budget, self.keep_last_turns = history_budget, keep_last_turns

    def build(self, ctx: ClientContext, question: str, history: list[Turn], chunks: list[Scored]) -> Prompt:
        client = (f"Клієнт: тариф {ctx.plan}, роль користувача {ctx.role}, "
                  f"модулі: {', '.join(ctx.modules) or 'базові'}.")
        system = SYSTEM + "\n" + client
        summary, recent = self._fit_history(history)
        used = {
            "system + клієнт": estimate_tokens(system),
            "підсумок історії": estimate_tokens(summary) if summary else 0,
            "останні репліки": sum(estimate_tokens(t.text) for t in recent),
            "питання": estimate_tokens(question),
        }
        room = self.budget - self.answer_reserve - sum(used.values())
        blocks, dropped, chunk_tokens = [], 0, 0
        for i, item in enumerate(chunks, start=1):
            c = item.chunk
            block = f"[{len(blocks) + 1}] ({c.source}: {c.title}{', ред. ' + c.meta['edition'] if 'edition' in c.meta else ''})\n{c.text}"
            cost = estimate_tokens(block)
            if chunk_tokens + cost > room:
                dropped = len(chunks) - i + 1
                break
            blocks.append(block)
            chunk_tokens += cost
        used["фрагменти бази знань"] = chunk_tokens
        used["резерв на відповідь"] = self.answer_reserve
        return Prompt(system, blocks, summary, recent, question,
                      tokens=sum(used.values()) - self.answer_reserve, dropped_chunks=dropped, sections=used)

    def _fit_history(self, history: list[Turn]) -> tuple[str, list[Turn]]:
        total = sum(estimate_tokens(t.text) for t in history)
        if total <= self.history_budget:
            return "", list(history)
        older, recent = history[:-self.keep_last_turns], history[-self.keep_last_turns:]
        # Останні репліки — дослівно, але кожна не довша за свою частку бюджету.
        summary_floor = min(200, self.history_budget // 4)
        cap = (self.history_budget - summary_floor) // self.keep_last_turns
        recent = [t if estimate_tokens(t.text) <= cap else Turn(t.role, t.text[: int(cap * 3.5) - 1] + "…")
                  for t in recent]
        summary_budget = self.history_budget - sum(estimate_tokens(t.text) for t in recent)
        summary = self._llm.summarize(older, max_tokens=summary_budget)
        if estimate_tokens(summary) > summary_budget:      # адаптер не дотримав ліміту — обрізаємо
            summary = summary[: int(summary_budget * 3.5)]
        return summary, recent
