"""Інжест демонстраційної бази знань PeopleFlow: chunking за типом контенту + знеособлення."""
from pathlib import Path

from rag.chunking import api_doc_chunks, section_chunks, ticket_chunks

KB = Path(__file__).resolve().parent / "data" / "sample_kb"


def load_chunks():
    chunks = api_doc_chunks((KB / "api_payroll_runs.md").read_text(encoding="utf-8"), "api_payroll_runs")
    for name in ("help_sick_leave", "help_vacation"):
        chunks += section_chunks((KB / f"{name}.md").read_text(encoding="utf-8"), name, "help")
    for name in ("policy_vacation", "policy_payroll_calendar"):
        chunks += section_chunks((KB / f"{name}.md").read_text(encoding="utf-8"), name, "policy")
    tickets, report = ticket_chunks((KB / "tickets.jsonl").read_text(encoding="utf-8"))
    return chunks + tickets, report
