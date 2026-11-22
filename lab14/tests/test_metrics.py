from rag.metrics import context_precision, faithfulness, mrr, recall_at_k, resolution_rate


def test_recall_at_k_catches_neighbouring_error_code():
    # Після зміни токенізатора на «ERR_4092» першим повертається фрагмент ERR_4091.
    ranked = ["api#ERR_4091", "api#ERR_4093", "ticket#T-1", "policy#2", "help#1"]
    assert recall_at_k(ranked, {"api#ERR_4092"}, k=5) == 0.0
    assert recall_at_k(["api#ERR_4092"] + ranked, {"api#ERR_4092"}, k=5) == 1.0


def test_mrr():
    assert mrr([(["a", "b"], {"b"}), (["c"], {"c"})]) == (0.5 + 1.0) / 2


def test_context_precision_prefers_relevant_chunks_on_top():
    assert context_precision([True, False, False]) == 1.0
    assert round(context_precision([False, False, True]), 2) == 0.33


def test_faithfulness_flags_one_invented_claim():
    # «24 дні» — є в політиці; «+2 дні за стаж» — вигадка моделі.
    assert faithfulness([True, False]) == 0.5


def test_resolution_rate_counts_users_who_came_back_with_a_ticket():
    conversations = [
        {"user": "u1", "topic": "sick_leave", "ended_at": "2026-11-02T10:00", "escalated": False},
        {"user": "u2", "topic": "sick_leave", "ended_at": "2026-11-02T11:00", "escalated": False},
        {"user": "u3", "topic": "vacation", "ended_at": "2026-11-02T12:00", "escalated": True},
    ]
    tickets = [{"user": "u1", "topic": "sick_leave", "created_at": "2026-11-03T09:00"}]
    assert resolution_rate(conversations, tickets) == 1 / 3
