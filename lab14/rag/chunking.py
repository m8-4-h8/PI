"""Завдання 1. Стратегії chunking для чотирьох типів контенту PeopleFlow."""
from __future__ import annotations

import json
import math
import re

from rag.domain import Chunk
from rag.pii import scrub


def estimate_tokens(text: str) -> int:
    """Груба оцінка: ~3.5 символу на токен для українського тексту з кодом."""
    return max(1, math.ceil(len(text) / 3.5))


# --- Наївний підхід, від якого відмовляємося -------------------------------------------
def fixed_size(text: str, size: int = 400, overlap: int = 50) -> list[str]:
    """Механічне різання на вікна по size символів з перекриттям."""
    step = size - overlap
    return [text[i:i + size] for i in range(0, max(len(text) - overlap, 1), step)]


# --- Допоміжне: розбір Markdown на секції ---------------------------------------------
def _split_sections(md: str, level: str) -> list[tuple[str, str]]:
    """[(заголовок, тіло)] за заголовками рівня level ('## ' чи '### ')."""
    sections, title, body = [], "", []
    for line in md.splitlines():
        if line.startswith(level):
            if title or any(b.strip() for b in body):
                sections.append((title, "\n".join(body).strip()))
            title, body = line[len(level):].strip(), []
        else:
            body.append(line)
    sections.append((title, "\n".join(body).strip()))
    return sections


def _doc_title(md: str) -> str:
    first = md.strip().splitlines()[0]
    return first.lstrip("# ").strip()


def _table(lines: list[str]) -> tuple[list[str], list[list[str]]]:
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines if ln.strip().startswith("|")]
    header, body = rows[0], [r for r in rows[2:]]
    return header, body


def _blocks(body: str) -> list[tuple[str, str]]:
    """Розбиває тіло на блоки, не розриваючи таблиці, код і нумеровані списки."""
    blocks, current, kind = [], [], None
    in_code = False
    for line in body.splitlines():
        if line.startswith("```"):
            if in_code:
                current.append(line)
                blocks.append(("code", "\n".join(current)))
                current, kind, in_code = [], None, False
                continue
            if current:
                blocks.append((kind, "\n".join(current)))
            current, kind, in_code = [line], "code", True
            continue
        if in_code:
            current.append(line)
            continue
        line_kind = "table" if line.strip().startswith("|") else "text"
        if not line.strip():
            if current:
                blocks.append((kind, "\n".join(current)))
            current, kind = [], None
            continue
        if kind not in (None, line_kind):
            blocks.append((kind, "\n".join(current)))
            current = []
        current.append(line)
        kind = line_kind
    if current:
        blocks.append((kind, "\n".join(current)))
    return blocks


# --- 1. Технічна документація API: структурний chunking --------------------------------
def api_doc_chunks(md: str, doc_id: str, max_tokens: int = 350) -> list[Chunk]:
    """Один chunk = один endpoint (опис + ВСЯ таблиця параметрів + приклад) і окремо по
    chunk на кожен код помилки. У кожному chunk — заголовок документа й endpoint, тож
    фрагмент зрозумілий без сусідів. Якщо endpoint не влазить у max_tokens, таблицю ріжемо
    по групах рядків і в кожній групі повторюємо шапку таблиці й назву endpoint."""
    title = _doc_title(md)
    chunks: list[Chunk] = []
    for endpoint, body in _split_sections(md, "## ")[1:]:
        method_path = endpoint.split(" — ")[0]
        main, *subs = _split_sections(body, "### ")
        head = f"{title}\n{endpoint}"
        blocks = _blocks(main[1])
        overview = head + "\n\n" + "\n\n".join(b for _, b in blocks)
        meta = {"endpoint": method_path, "kind": "endpoint"}
        if estimate_tokens(overview) <= max_tokens:
            chunks.append(Chunk(f"{doc_id}#{method_path}", overview, "api", endpoint, meta))
        else:
            # Опис і приклад — окремо; таблицю ріжемо по групах рядків, повторюючи шапку й endpoint.
            prose = head + "\n\n" + "\n\n".join(b for k, b in blocks if k != "table")
            chunks.append(Chunk(f"{doc_id}#{method_path}", prose, "api", endpoint, meta))
            for kind, block in blocks:
                if kind != "table":
                    continue
                header, rows = _table(block.splitlines())
                hdr = "| " + " | ".join(header) + " |\n|" + "---|" * len(header)
                groups, group = [], []
                for row in rows:
                    line = "| " + " | ".join(row) + " |"
                    if group and estimate_tokens(head + "\n" + hdr + "\n" + "\n".join(group + [line])) > max_tokens:
                        groups.append(group)
                        group = []
                    group.append(line)
                groups.append(group)
                for n, g in enumerate(groups, start=1):
                    chunks.append(Chunk(f"{doc_id}#{method_path}#params{n}",
                                        head + " — параметри\n\n" + hdr + "\n" + "\n".join(g), "api",
                                        f"{endpoint} — параметри ({n})", {**meta, "kind": "params"}))
        for sub_title, sub_body in subs:
            if "помил" not in sub_title.lower():
                continue
            header, rows = _table([ln for ln in sub_body.splitlines() if ln.strip().startswith("|")])
            for row in rows:
                fields = dict(zip(header, row))
                code = fields.get("Код", row[0])
                text = (f"{title}\n{method_path} — помилка {code} (HTTP {fields.get('HTTP', '')}).\n"
                        + "\n".join(f"{k}: {v}" for k, v in fields.items() if k not in ("Код", "HTTP")))
                chunks.append(Chunk(f"{doc_id}#{method_path}#{code}", text, "api", f"{method_path} {code}",
                                    {"endpoint": method_path, "error_codes": [code], "kind": "error"}))
    return chunks


# --- 2. Статті довідкового центру і 3. вікі політик: за заголовками ------------------
def section_chunks(md: str, doc_id: str, source: str) -> list[Chunk]:
    """Chunk = секція ## разом з усім нумерованим списком кроків, з назвою статті на початку.
    Для політик у метадані йде дата редакції — при оновленні старі chunks замінюються в одній транзакції."""
    title = _doc_title(md)
    edition = re.search(r"редакція від (\d{4}-\d{2}-\d{2})", title)
    intro, *sections = _split_sections(md, "## ")
    intro_text = "\n".join(ln for ln in intro[1].splitlines() if not ln.startswith("# ")).strip()
    chunks = []
    for i, (sec_title, body) in enumerate(sections, start=1):
        text = f"{title}\n{sec_title}\n\n{body}"
        if i == 1 and intro_text:
            text = f"{title}\n{intro_text}\n\n{sec_title}\n\n{body}"
        meta = {"edition": edition.group(1)} if edition else {}
        chunks.append(Chunk(f"{doc_id}#{i}", text, source, f"{title} — {sec_title}", meta))
    return chunks


# --- 4. Історія тікетів: пара «питання — відповідь», знеособлена, без дублів ------------
def _token_set(text: str) -> set[str]:
    """Коди помилок — цілими, слова — грубою основою (перші 6 літер)."""
    codes = set(re.findall(r"err_\d{4}", text.lower()))
    words = {w[:6] for w in re.findall(r"[^\W\d_][\w']*", text.lower()) if len(w) > 2 and not w.startswith("err_")}
    return codes | words


def ticket_chunks(jsonl: str, similarity: float = 0.5) -> tuple[list[Chunk], dict]:
    chunks: list[Chunk] = []
    report = {"pii_removed": 0, "merged": []}
    for line in jsonl.strip().splitlines():
        t = json.loads(line)
        question, found_q = scrub(t["question"])
        answer, found_a = scrub(t["answer"])
        report["pii_removed"] += len(found_q) + len(found_a)
        tokens = _token_set(question)
        duplicate = next((c for c in chunks
                          if len(tokens & c.meta["tokens"]) / max(len(tokens | c.meta["tokens"]), 1) >= similarity),
                         None)
        if duplicate is not None:
            duplicate.meta["duplicates"].append(t["id"])
            report["merged"].append((t["id"], duplicate.id))
            continue
        codes = re.findall(r"\bERR_\d{4}\b", question + " " + answer)
        text = f"Питання клієнта: {question}\nВідповідь підтримки: {answer}"
        chunks.append(Chunk(f"ticket#{t['id']}", text, "ticket", f"Тікет {t['id']}",
                            {"tokens": tokens, "duplicates": [], "error_codes": codes, "tags": t["tags"]}))
    return chunks, report
