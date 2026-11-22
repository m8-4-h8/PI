from kb import KB
from rag.chunking import api_doc_chunks, estimate_tokens, fixed_size, section_chunks, ticket_chunks
from rag.pii import scrub

API = (KB / "api_payroll_runs.md").read_text(encoding="utf-8")


def test_fixed_size_separates_parameter_rows_from_header_and_endpoint():
    chunks = fixed_size(API)
    orphan = [c for c in chunks if "| tax_profile" in c or "| dry_run" in c]
    assert any("| Параметр" not in c and "POST /v2/payroll/runs —" not in c for c in orphan)


def test_structured_api_chunks_keep_header_and_endpoint_in_every_fragment():
    chunks = api_doc_chunks(API, "api", max_tokens=150)
    for c in chunks:
        assert "Payroll API v2" in c.text and c.meta["endpoint"] in c.text
        if "| period" in c.text or "| dry_run" in c.text:
            assert "| Параметр | Тип | Обов'язковий | Опис |" in c.text
        assert estimate_tokens(c.text) <= 150


def test_each_error_code_is_its_own_chunk_with_meaning_and_fix():
    errors = {c.meta["error_codes"][0]: c for c in api_doc_chunks(API, "api") if c.meta["kind"] == "error"}
    assert set(errors) == {"ERR_4091", "ERR_4092", "ERR_4093", "ERR_4221", "ERR_4041"}
    assert "Що робити: Відкрийте період" in errors["ERR_4092"].text
    assert "ERR_4091" not in errors["ERR_4092"].text


def test_help_article_keeps_numbered_steps_together_with_title():
    md = (KB / "help_sick_leave.md").read_text(encoding="utf-8")
    first = section_chunks(md, "sick", "help")[0]
    assert first.text.startswith("Як провести електронний лікарняний")
    assert all(f"{n}." in first.text for n in range(1, 5))


def test_policy_chunks_carry_edition_date():
    md = (KB / "policy_vacation.md").read_text(encoding="utf-8")
    assert {c.meta["edition"] for c in section_chunks(md, "vac", "policy")} == {"2026-09-01"}


def test_pii_is_scrubbed_and_near_duplicate_tickets_are_merged():
    chunks, report = ticket_chunks((KB / "tickets.jsonl").read_text(encoding="utf-8"))
    text = "\n".join(c.text for c in chunks)
    for leaked in ("olena.koval@", "3124509876", "UA213223130000026007233566001", "123 45 67", "Олена Коваль"):
        assert leaked not in text
    assert report["merged"] == [("T-10877", "ticket#T-10231")]


def test_regex_scrubber_does_not_catch_names_in_free_form_so_ner_is_needed():
    text, _ = scrub("Лікарняний Петренка не підтягнувся")
    assert "Петренка" in text
