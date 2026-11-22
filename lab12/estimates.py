"""Завдання 2. Back-of-the-envelope: усі кроки арифметики друкуються."""

DAU = 1_000_000
REQ_PER_USER = 20
SECONDS_PER_DAY = 86_400
PEAK_FACTOR = 5
FLASH_USERS, FLASH_REQ, FLASH_WINDOW = 1_000_000, 2, 60
EVENTS_PER_YEAR, SEATS_SOLD_PER_EVENT, YEARS = 50_000, 1_000, 5

KB, MB, GB, TB = 1_000, 1_000_000, 1_000_000_000, 1_000_000_000_000


def num(value) -> str:
    text = f"{value:,.0f}" if abs(value - round(value)) < 1e-9 or value >= 100 else f"{value:,.1f}"
    return text.replace(",", " ")


def show(label, expr, value, unit=""):
    print(f"{label:<50} {expr.replace(',', ' '):<32} = {num(value)} {unit}")
    return value


print("1. Середній QPS")
req_day = show("  запитів на день", f"{DAU:,} × {REQ_PER_USER}", DAU * REQ_PER_USER)
avg_qps = show("  середній QPS", f"{req_day:,} / {SECONDS_PER_DAY:,}", req_day / SECONDS_PER_DAY, "QPS")

print("\n2. Піковий QPS звичайного дня")
peak_qps = show("  пік", f"{avg_qps:.0f} × {PEAK_FACTOR}", avg_qps * PEAK_FACTOR, "QPS")

print("\n3. Flash-sale")
flash_req = show("  запитів за вікно", f"{FLASH_USERS:,} × {FLASH_REQ}", FLASH_USERS * FLASH_REQ)
flash_qps = show("  середній QPS за 60 с", f"{flash_req:,} / {FLASH_WINDOW}", flash_req / FLASH_WINDOW, "QPS")
burst_qps = show("  сплеск у перші 10 с (половина запитів)", f"{flash_req // 2:,} / 10", flash_req / 2 / 10, "QPS")
show("  у скільки разів більше звичайного піку", f"{flash_qps:.0f} / {peak_qps:.0f}", flash_qps / peak_qps, "×")
show("  сплеск vs звичайний пік", f"{burst_qps:.0f} / {peak_qps:.0f}", burst_qps / peak_qps, "×")
show("  бажаючих на одне місце", f"{FLASH_USERS:,} / 50 000", FLASH_USERS / 50_000, "людей")

print("\n4. Транзакційні дані за 5 років")
tickets = show("  квитків", f"{EVENTS_PER_YEAR:,} × {SEATS_SOLD_PER_EVENT:,} × {YEARS}", EVENTS_PER_YEAR * SEATS_SOLD_PER_EVENT * YEARS)
orders = show("  замовлень (у середньому 2 квитки)", f"{tickets:,} / 2", tickets / 2)
seats = show("  рядків місць (місткість ≈ 2× проданих)", f"{tickets:,} × 2", tickets * 2)
t_bytes = show("  квитки по 500 Б", f"{tickets:,} × 500 Б", tickets * 500 / GB, "ГБ")
o_bytes = show("  замовлення по 1 КБ (з платежем, історією)", f"{orders:,.0f} × 1 КБ", orders * KB / GB, "ГБ")
s_bytes = show("  місця по 200 Б", f"{seats:,} × 200 Б", seats * 200 / GB, "ГБ")
raw = show("  разом сирих даних", f"{t_bytes:.0f} + {o_bytes:.0f} + {s_bytes:.0f}", t_bytes + o_bytes + s_bytes, "ГБ")
with_idx = show("  + індекси (+50%)", f"{raw:.0f} × 1.5", raw * 1.5, "ГБ")
replicated = show("  × 3 копії (primary + 2 репліки)", f"{with_idx:.0f} × 3", with_idx * 3, "ГБ")

print("\n5. Медіа за рік")
per_event = show("  на захід: афіша 3 розміри 1 МБ + 5 фото × 0.5 МБ", "1 + 5 × 0.5", 3.5, "МБ")
media = show("  афіші й фото", f"{EVENTS_PER_YEAR:,} × {per_event} МБ", EVENTS_PER_YEAR * per_event * MB / GB, "ГБ")
maps = show("  схеми залів (5 000 залів × 1 МБ SVG)", "5 000 × 1 МБ", 5_000 * MB / GB, "ГБ")
show("  разом за рік", f"{media:.0f} + {maps:.0f}", media + maps, "ГБ")

print("\n6. Bandwidth")
show("  звичайний середній (20 КБ відповідь)", f"{avg_qps:.0f} × 20 КБ × 8", avg_qps * 20 * KB * 8 / MB, "Мбіт/с")
show("  звичайний пік", f"{peak_qps:.0f} × 20 КБ × 8", peak_qps * 20 * KB * 8 / MB, "Мбіт/с")
show("  flash-sale БЕЗ черги (100 КБ: сторінка + мапа)", f"{flash_qps:.0f} × 100 КБ × 8", flash_qps * 100 * KB * 8 / GB, "Гбіт/с")
show("  flash-sale з чергою: CDN (50 КБ waiting room)", f"{flash_qps:.0f} × 50 КБ × 8", flash_qps * 50 * KB * 8 / GB, "Гбіт/с")
show("  flash-sale з чергою: origin (1 КБ API)", f"{flash_qps:.0f} × 1 КБ × 8", flash_qps * 1 * KB * 8 / MB, "Мбіт/с")
