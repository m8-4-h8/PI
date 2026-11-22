"""Знеособлення історії тікетів перед індексацією.

Регулярні вирази ловлять лише структуровані ідентифікатори. Імена в довільних відмінках
(«лікарняний Петренка») ними не зловити: у проді після регулярок працює NER-модель
(наприклад, Microsoft Presidio з українськими розпізнавачами), а сумнівні тікети йдуть на ручну перевірку.
"""
import re

PATTERNS = [
    ("[EMAIL]", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("[IBAN]", re.compile(r"\bUA\d{27}\b")),
    ("[ТЕЛЕФОН]", re.compile(r"\+?380[\s-]?\(?\d{2}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}\b")),
    ("[РНОКПП]", re.compile(r"\b\d{10}\b")),
    ("[ІМ'Я]", re.compile(r"(?<=\bя )[А-ЯІЇЄҐ][а-яіїєґ']+ [А-ЯІЇЄҐ][а-яіїєґ']+")),
]


def scrub(text: str) -> tuple[str, list[str]]:
    found = []
    for label, pattern in PATTERNS:
        text, n = pattern.subn(label, text)
        found += [label] * n
    return text, found
