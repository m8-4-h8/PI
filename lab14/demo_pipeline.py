"""Завдання 3: повний конвеєр запиту на демонстраційній базі знань PeopleFlow.

Моделі замінено заглушками (див. adapters/memory.py): демо перевіряє оркестрацію — гібридний пошук,
закріплення точного коду помилки, поріг впевненості, ескалацію, бюджет промпту, заміну LLM-адаптера.

python demo_pipeline.py   -> results/pipeline_demo.txt
"""
from adapters.memory import (BM25Index, HashingEmbedding, InMemoryEscalation, InMemoryVectorStore,
                             OverlapReranker, ScriptedLLM, TemplateLLM)
from kb import load_chunks
from rag.domain import ClientContext, Turn
from rag.metrics import mrr, recall_at_k
from rag.use_case import AnswerSupportQuestion

CTX = ClientContext("tenant-agro-sv", plan="business", role="payroll_admin", modules=("payroll", "hr"))

GOLDEN = {
    "точні ідентифікатори (коди, параметри)": [
        ("ERR_4092", {"api_payroll_runs#POST /v2/payroll/runs#ERR_4092"}),
        ("що означає ERR_4221", {"api_payroll_runs#POST /v2/payroll/runs#ERR_4221"}),
        ("ERR_4041 при отриманні розрахунку", {"api_payroll_runs#GET /v2/payroll/runs/{id}#ERR_4041"}),
        ("який формат у параметра period", {"api_payroll_runs#POST /v2/payroll/runs"}),
        ("для чого dry_run", {"api_payroll_runs#POST /v2/payroll/runs"}),
    ],
    "перефразовані, без слів з документа": [
        ("скільки вихідних на рік дають для відпочинку", {"policy_vacation#1"}),
        ("коли приходять гроші на картку", {"policy_payroll_calendar#1"}),
        ("захворів, що робити з документом від лікаря", {"help_sick_leave#1"}),
        ("місяць заблоковано, не дає перерахувати платню", {"api_payroll_runs#POST /v2/payroll/runs#ERR_4092",
                                                          "policy_payroll_calendar#2"}),
        ("чи можна взяти гроші замість невикористаного відпочинку", {"policy_vacation#3"}),
    ],
}


def build(llm=None):
    chunks, report = load_chunks()
    embedder = HashingEmbedding()
    llm = llm or ScriptedLLM()
    escalation = InMemoryEscalation()
    bot = AnswerSupportQuestion(embedder, InMemoryVectorStore(chunks, embedder), BM25Index(chunks),
                                OverlapReranker(), llm, escalation)
    return bot, chunks, report, escalation


def show(bot, title, question, history=()):
    print(f"\n### {title}\nПитання: {question}")
    if history:
        print(f"Реплік в історії: {len(history)}")
    answer = bot.ask(CTX, question, list(history))
    for s in answer.retrieved[:3]:
        print(f"   top: {s.score:.2f}  {s.chunk.id}")
    print(f"Впевненість: {answer.confidence:.2f}")
    if answer.escalated:
        print(f"-> ЕСКАЛАЦІЯ ({answer.reason}): {answer.text}")
    else:
        print(f"-> ВІДПОВІДЬ: {answer.text}\n   джерела: {answer.citations}")
        p = answer.prompt
        parts = ", ".join(f"{k} {v}" for k, v in p.sections.items())
        print(f"   промпт ~{p.tokens} токенів ({parts}); відкинуто фрагментів: {p.dropped_chunks}")
        if p.history_summary:
            print(f"   підсумок історії: «{p.history_summary[:110]}…»")
    return answer


def main():
    bot, chunks, report, escalation = build()
    by_source = {}
    for c in chunks:
        by_source[c.source] = by_source.get(c.source, 0) + 1
    print(f"Фрагментів у базі: {len(chunks)} {by_source}")
    print(f"Знеособлено PII у тікетах: {report['pii_removed']}; злито дублікатів: {report['merged']}")

    show(bot, "1. Точний код помилки", "Отримую ERR_4092 при POST /v2/payroll/runs, що робити?")
    show(bot, "2. Перефразоване питання без коду", "Не можу порахувати зарплату за жовтень, пише що місяць закритий")
    show(bot, "3. Питання поза базою знань", "Як налаштувати вивантаження в 1С через SFTP?")
    show(bot, "4. Тема лише для оператора", "Хочу повернення коштів за минулий місяць підписки")
    long_history = []
    for i in range(12):
        long_history.append(Turn("user", f"Питання {i + 1} про відпустки і графік команди: " + "деталі " * 60))
        long_history.append(Turn("assistant", "Відповідь бота з кроками і посиланнями. " + "пояснення " * 60))
    show(bot, "5. Довга історія діалогу (24 репліки)", "А яка тривалість щорічної відпустки за політикою?", long_history)

    print("\n### 6. Заміна LLM-провайдера: той самий use case, інший адаптер")
    bot_b, *_ = build(TemplateLLM())
    a = bot_b.ask(CTX, "Отримую ERR_4092 при POST /v2/payroll/runs, що робити?", [])
    print(f"-> {a.text!r}\n   джерела: {a.citations}")

    print("\n### Ескалації, створені за прогін")
    for r in escalation.requests:
        print(f"   [{r.priority}] {r.reason}: «{r.question}», фрагментів передано оператору: {len(r.retrieved)}")

    print("\n### Retrieval-метрики лише sparse-пошуку (BM25) на золотому наборі")
    index = BM25Index(chunks)
    for group, items in GOLDEN.items():
        results = [([s.chunk.id for s in index.search(q, 5, CTX.tenant_id)], rel) for q, rel in items]
        recall = sum(recall_at_k(r, rel, 5) > 0 for r, rel in results) / len(results)
        print(f"   {group:<40} Hit@5 = {recall:.0%}, MRR = {mrr(results):.2f}")
        for (q, rel), (ranked, _) in zip(items, results):
            pos = next((i for i, cid in enumerate(ranked, 1) if cid in rel), None)
            print(f"      {'знайдено на ' + str(pos) + ' місці' if pos else 'НЕ знайдено в top-5':<22} {q}")


if __name__ == "__main__":
    main()
