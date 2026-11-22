import pytest

from adapters.memory import (BM25Index, HashingEmbedding, InMemoryEscalation, InMemoryVectorStore,
                             OverlapReranker, ScriptedLLM, TemplateLLM)
from kb import load_chunks
from rag.domain import Chunk, ClientContext, Scored, Turn
from rag.fusion import rrf
from rag.prompt import PromptBuilder
from rag.use_case import AnswerSupportQuestion

CTX = ClientContext("tenant-a", plan="business", role="payroll_admin")


def make_bot(llm=None, prompt_builder=None):
    chunks, _ = load_chunks()
    embedder = HashingEmbedding()
    llm = llm or ScriptedLLM()
    escalation = InMemoryEscalation()
    bot = AnswerSupportQuestion(embedder, InMemoryVectorStore(chunks, embedder), BM25Index(chunks),
                                OverlapReranker(), llm, escalation, prompt_builder=prompt_builder)
    return bot, escalation, llm


def test_exact_error_code_answer_cites_official_api_fragment():
    bot, _, _ = make_bot()
    answer = bot.ask(CTX, "Отримую ERR_4092 при POST /v2/payroll/runs, що робити?", [])
    assert not answer.escalated
    assert answer.citations == ["api_payroll_runs#POST /v2/payroll/runs#ERR_4092"]
    assert "reopen" in answer.text


def test_low_confidence_escalates_with_transcript_and_retrieved_context():
    bot, escalation, llm = make_bot()
    history = [Turn("user", "Добрий день"), Turn("assistant", "Вітаю! Чим допомогти?")]
    answer = bot.ask(CTX, "Як налаштувати вивантаження в 1С через SFTP?", history)
    assert answer.escalated and answer.reason == "низька впевненість пошуку"
    request = escalation.requests[0]
    assert len(request.transcript) == 3 and request.retrieved
    assert llm.prompts == []                    # LLM навіть не викликали


@pytest.mark.parametrize("question", ["Хочу повернення коштів за тариф", "Будемо подавати до суду"])
def test_money_and_legal_topics_always_go_to_human(question):
    bot, escalation, _ = make_bot()
    assert bot.ask(CTX, question, []).escalated
    assert escalation.requests[0].reason == "тема лише для оператора"


def test_payroll_escalation_gets_high_priority():
    bot, escalation, _ = make_bot()
    bot.ask(CTX, "Зарплата не рахується через SFTP-шлюз у 1С", [])
    assert escalation.requests[0].priority == "high"


def test_insufficient_context_from_llm_leads_to_escalation():
    class Refusing(ScriptedLLM):
        def complete(self, prompt):
            return "INSUFFICIENT_CONTEXT"

    bot, escalation, _ = make_bot(llm=Refusing())
    answer = bot.ask(CTX, "Яка тривалість щорічної відпустки за політикою?", [])
    assert answer.escalated and "немає відповіді" in answer.reason


def test_long_history_is_summarized_and_prompt_fits_budget():
    builder_llm = ScriptedLLM()
    builder = PromptBuilder(builder_llm, budget=3_000, answer_reserve=500, history_budget=800)
    bot, _, _ = make_bot(llm=builder_llm, prompt_builder=builder)
    history = [Turn("user" if i % 2 == 0 else "assistant", "довга репліка " * 80) for i in range(30)]
    answer = bot.ask(CTX, "Яка тривалість щорічної відпустки за політикою?", history)
    prompt = answer.prompt
    assert prompt.history_summary and len(prompt.recent_turns) == 3
    assert prompt.tokens + builder.answer_reserve <= builder.budget
    assert prompt.sections["підсумок історії"] + prompt.sections["останні репліки"] <= 800


def test_lowest_ranked_chunks_are_dropped_first_when_budget_is_tight():
    llm = ScriptedLLM()
    builder = PromptBuilder(llm, budget=1_200, answer_reserve=300)
    chunks = [Scored(Chunk(f"c{i}", "текст " * 120, "help", f"Стаття {i}"), 1 - i / 10) for i in range(5)]
    prompt = builder.build(CTX, "питання", [], chunks)
    assert prompt.dropped_chunks > 0
    assert prompt.context_blocks[0].startswith("[1] (help: Стаття 0")


def test_switching_llm_provider_changes_only_the_adapter():
    bot_a, _, llm_a = make_bot(ScriptedLLM())
    bot_b, _, llm_b = make_bot(TemplateLLM())
    question = "Отримую ERR_4092 при POST /v2/payroll/runs, що робити?"
    a, b = bot_a.ask(CTX, question, []), bot_b.ask(CTX, question, [])
    assert a.text != b.text and a.citations == b.citations
    assert llm_a.prompts[0].context_blocks == llm_b.prompts[0].context_blocks


def test_rrf_rewards_documents_found_by_both_retrievers():
    a, b, c = (Chunk(x, x, "help", x) for x in "abc")
    fused = rrf([[Scored(a, 0.9), Scored(b, 0.8)], [Scored(b, 12.0), Scored(c, 11.0)]])
    assert [s.chunk.id for s in fused] == ["b", "a", "c"]


def test_tenant_private_chunks_are_not_visible_to_other_tenants():
    private = Chunk("t1-only", "ERR_4092 у нашій інсталяції", "ticket", "x", {"tenant_id": "tenant-b"})
    index = BM25Index([private, Chunk("pub", "загальна стаття", "help", "y")])
    assert index.search("ERR_4092", 5, "tenant-a") == []
    assert index.search("ERR_4092", 5, "tenant-b")[0].chunk.id == "t1-only"
