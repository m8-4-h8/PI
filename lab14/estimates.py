"""Завдання 2. Обсяг бази знань PeopleFlow після chunking і навантаження на пошук."""
import math

ARTICLES, ARTICLE_WORDS, WORDS_PER_SECTION = 340, 500, 180
API_PAGES, ENDPOINTS_PER_PAGE, TABLE_SPLIT, ERRORS_PER_PAGE = 85, 2, 1.3, 4
TICKETS, DUP_SHARE, NOISE_SHARE = 12_000, 0.6, 0.3
WIKI_PAGES, WIKI_WORDS, WORDS_PER_CLAUSE = 25, 800, 150
DIM, BYTES_PER_FLOAT, HNSW_OVERHEAD, CHUNK_TEXT_KB = 1024, 4, 1.5, 2
REQUESTS_WEEK, TURNS, WORK_HOURS_WEEK, PEAK_FACTOR = 3_000, 2.5, 50, 50


def num(v):
    if abs(v - round(v)) < 1e-9 or abs(v) >= 100:
        s = f"{v:,.0f}"
    else:
        s = f"{v:,.2f}" if abs(v) < 1 else f"{v:,.1f}"
    return s.replace(",", " ")


def show(label, expr, value, unit=""):
    print(f"{label:<58} {expr:<30} = {num(value)} {unit}".rstrip())
    return value


print("1. Фрагментів після chunking")
help_c = show("  статті: слів", f"{ARTICLES} × {ARTICLE_WORDS}", ARTICLES * ARTICLE_WORDS)
help_c = show("  статті: секцій по ~180 слів", f"{num(help_c)} / {WORDS_PER_SECTION}", math.ceil(help_c / WORDS_PER_SECTION))
ep = show("  API: endpoint-фрагментів (+30% на довгі таблиці)", f"{API_PAGES} × {ENDPOINTS_PER_PAGE} × {TABLE_SPLIT}",
          round(API_PAGES * ENDPOINTS_PER_PAGE * TABLE_SPLIT))
er = show("  API: по фрагменту на код помилки", f"{API_PAGES} × {ERRORS_PER_PAGE}", API_PAGES * ERRORS_PER_PAGE)
api_c = show("  API разом", f"{ep} + {er}", ep + er)
uniq = show("  тікети: після злиття дублікатів (−60%)", f"{TICKETS:,} × 0.4".replace(",", " "), TICKETS * (1 - DUP_SHARE))
tick_c = show("  тікети: без «дякую, закриваємо» і разових (−30%)", f"{num(uniq)} × 0.7", round(uniq * (1 - NOISE_SHARE)))
wiki_c = show("  вікі політик: пунктів по ~150 слів", f"{WIKI_PAGES} × {WIKI_WORDS} / {WORDS_PER_CLAUSE}",
              math.ceil(WIKI_PAGES * WIKI_WORDS / WORDS_PER_CLAUSE))
total = show("  разом", f"{help_c} + {api_c} + {tick_c} + {wiki_c}", help_c + api_c + tick_c + wiki_c)
raw_total = show("  для порівняння: без злиття тікетів", f"{help_c} + {api_c} + {TICKETS:,} + {wiki_c}".replace(",", " "),
                 help_c + api_c + TICKETS + wiki_c)

print("\n2. Пам'ять")
vec = show("  один вектор", f"{DIM} × {BYTES_PER_FLOAT} Б", DIM * BYTES_PER_FLOAT / 1024, "КБ")
show("  усі вектори + HNSW", f"{num(total)} × 4 КБ × {HNSW_OVERHEAD}", total * vec * HNSW_OVERHEAD / 1024, "МБ")
show("  навіть без злиття тікетів", f"{num(raw_total)} × 4 КБ × {HNSW_OVERHEAD}", raw_total * vec * HNSW_OVERHEAD / 1024, "МБ")
show("  тексти фрагментів", f"{num(total)} × {CHUNK_TEXT_KB} КБ", total * CHUNK_TEXT_KB / 1024, "МБ")

print("\n3. Навантаження")
q_week = show("  питань до бота на тиждень", f"{REQUESTS_WEEK:,} × {TURNS}".replace(",", " "), REQUESTS_WEEK * TURNS)
q_hour = show("  у робочу годину", f"{num(q_week)} / {WORK_HOURS_WEEK}", q_week / WORK_HOURS_WEEK)
avg_qps = show("  середній QPS", f"{num(q_hour)} / 3 600", q_hour / 3600, "QPS")
show("  пік: день виплат + понеділок зранку, хвилинний сплеск", f"{avg_qps:.3f} × {PEAK_FACTOR}", avg_qps * PEAK_FACTOR, "QPS")
show("  закладаємо з запасом", "", 5, "QPS (2 пошуки на запит = 10 запитів до БД/с)")
