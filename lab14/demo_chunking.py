"""Завдання 1: чому fixed-size chunking небезпечний для документації API з таблицею параметрів.

python demo_chunking.py   -> results/chunking_demo.txt
"""
from pathlib import Path

from rag.chunking import api_doc_chunks, estimate_tokens, fixed_size

DOC = Path(__file__).resolve().parent / "data" / "sample_kb" / "api_payroll_runs.md"


def problems(chunk: str) -> list[str]:
    found = []
    lines = chunk.splitlines()
    first_header = next((i for i, ln in enumerate(lines) if "| Параметр" in ln or "| Код" in ln), len(lines))
    first_endpoint = next((i for i, ln in enumerate(lines) if "POST /v2" in ln or "GET /v2" in ln), len(lines))
    rows = [i for i, ln in enumerate(lines) if ln.strip().startswith("|") and "---" not in ln
            and "| Параметр" not in ln and "| Код" not in ln]
    if rows and rows[0] < first_header:
        found.append("рядки таблиці без шапки: невідомо, що означає кожна колонка")
    if rows and rows[0] < first_endpoint:
        found.append("рядки без назви свого endpoint: це POST /runs чи GET /runs/{id}?")
    if rows and rows[0] < first_endpoint < len(lines) and lines[first_endpoint].startswith("## "):
        found.append(f"змішано два endpoint: рядки попереднього і заголовок «{lines[first_endpoint][3:30]}…»")
    first, last = lines[0], lines[-1]
    if first and not first.startswith(("|", "#", "`", "Payroll API v2")):
        found.append(f"починається посеред рядка: «{first[:40]}…»")
    if last.strip().startswith("|") and not last.rstrip().endswith("|"):
        found.append(f"рядок таблиці розрізано: «…{last[-45:]}»")
    if chunk.count("```") % 2 == 1:
        found.append("розрізано блок коду")
    return found


def main():
    text = DOC.read_text(encoding="utf-8")
    print("=" * 100)
    print("А. Fixed-size: 400 символів, перекриття 50 (типове налаштування з туторіалів)")
    print("=" * 100)
    bad = 0
    for i, chunk in enumerate(fixed_size(text), start=1):
        issues = problems(chunk)
        bad += bool(issues)
        print(f"\n--- chunk {i}: {len(chunk)} символів, ~{estimate_tokens(chunk)} токенів")
        print(chunk)
        for issue in issues:
            print(f"   !!! {issue}")
    print(f"\nПроблемних фрагментів: {bad} з {len(fixed_size(text))}")

    print("\n" + "=" * 100)
    print("Б. Структурний chunking: endpoint цілком + окремий фрагмент на кожен код помилки")
    print("=" * 100)
    chunks = api_doc_chunks(text, "api_payroll_runs")
    for c in chunks:
        print(f"\n--- {c.id}: ~{estimate_tokens(c.text)} токенів, метадані {c.meta}")
        print(c.text)
        assert not problems(c.text), problems(c.text)
    print(f"\nФрагментів: {len(chunks)}, проблемних: 0")

    print("\n" + "=" * 100)
    print("В. Та сама таблиця при ліміті 150 токенів: ріжемо по рядках, шапку й endpoint повторюємо")
    print("=" * 100)
    for c in api_doc_chunks(text, "api_payroll_runs", max_tokens=150):
        if c.meta["kind"] == "error":
            continue
        print(f"\n--- {c.id}: ~{estimate_tokens(c.text)} токенів")
        print(c.text)
        assert not problems(c.text), problems(c.text)

if __name__ == "__main__":
    main()
