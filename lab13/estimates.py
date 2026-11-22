"""Завдання 2. Back-of-the-envelope для месенджера: усі кроки арифметики друкуються."""

REGISTERED = 50_000_000
DAU = 5_000_000
MSG_PER_USER = 40
SECONDS_PER_DAY = 86_400

# Припущення (пояснені в README, Завдання 2)
PEAK_FACTOR = 3            # вечірня година пік
HOLIDAY_FACTOR = 10        # Новий рік, 00:00
SHARE_1TO1 = 0.7           # частка повідомлень 1-на-1
GROUP_RECIPIENTS = 9       # середня група з 10 учасників -> 9 отримувачів
ONLINE_HOURS = 2.5         # скільки годин на добу користувач тримає з'єднання
CONCURRENCY_PEAK = 2       # пік одночасних / середнє
DEVICES = 1.3              # телефон + інколи desktop/web
CONN_PER_NODE = 50_000     # з'єднань на один вузол Connection Gateway
CONN_MEMORY_KB = 30        # TLS + буфери + стан сесії
HEARTBEAT_S = 30
MSG_BYTES = 200            # 100 Б тексту + 100 Б метаданих
REPLICATION = 3
COMPACTION_HEADROOM = 1.3
MEDIA_SHARE, MEDIA_KB = 0.1, 300
CONTACTS, ONLINE_SHARE = 150, 0.2
TRANSITIONS = 50           # змін online/offline на добу (25 відкриттів застосунку)
SUBSCRIBERS = 3            # з онлайн-контактів, у кого відкритий цей чат чи список чатів
TRANSITIONS_AFTER_GRACE = 16

KB, MB, GB, TB, PB = 1_000, 10**6, 10**9, 10**12, 10**15


def num(value) -> str:
    if abs(value - round(value)) < 1e-9 or abs(value) >= 100:
        text = f"{value:,.0f}"
    else:
        text = f"{value:,.1f}"
    return text.replace(",", " ")


def show(label, expr, value, unit=""):
    print(f"{label:<54} {expr.replace(',', ' '):<34} = {num(value)} {unit}".rstrip())
    return value


print("1. QPS повідомлень")
per_day = show("  повідомлень на добу", f"{DAU:,} × {MSG_PER_USER}", DAU * MSG_PER_USER)
avg = show("  середній QPS (надсилання)", f"{per_day:,} / {SECONDS_PER_DAY:,}", per_day / SECONDS_PER_DAY, "msg/s")
peak = show("  пік вечірньої години", f"{avg:.0f} × {PEAK_FACTOR}", avg * PEAK_FACTOR, "msg/s")
holiday = show("  сплеск у Новий рік", f"{avg:.0f} × {HOLIDAY_FACTOR}", avg * HOLIDAY_FACTOR, "msg/s")
fanout = show("  доставок на одне повідомлення", f"{SHARE_1TO1} × 1 + {1 - SHARE_1TO1:.1f} × {GROUP_RECIPIENTS}",
              round(SHARE_1TO1 * 1 + (1 - SHARE_1TO1) * GROUP_RECIPIENTS, 2))
show("  доставок/с у середньому", f"{avg:.0f} × {fanout}", avg * fanout, "deliveries/s")
peak_deliv = show("  доставок/с у пік", f"{peak:.0f} × {fanout}", peak * fanout, "deliveries/s")
show("  доставок/с у Новий рік", f"{holiday:.0f} × {fanout}", holiday * fanout, "deliveries/s")
show("  квитанції delivered + read у пік (×2 до доставок)", f"{peak_deliv:.0f} × 2", peak_deliv * 2, "events/s")

print("\n2. Одночасні WebSocket-з'єднання")
avg_online = show("  у середньому онлайн користувачів", f"{DAU:,} × {ONLINE_HOURS} / 24", DAU * ONLINE_HOURS / 24)
peak_online = show("  у пік", f"{avg_online:.0f} × {CONCURRENCY_PEAK}", avg_online * CONCURRENCY_PEAK)
show("  частка DAU онлайн у пік", f"{peak_online:.0f} / {DAU:,}", peak_online / DAU * 100, "%")
conns = show("  з'єднань (пристроїв на користувача)", f"{peak_online:.0f} × {DEVICES}", peak_online * DEVICES)
nodes = show("  вузлів Connection Gateway", f"{conns:.0f} / {CONN_PER_NODE:,}", conns / CONN_PER_NODE)
show("  + запас на втрату 1 з 3 зон (× 1.5), округлено", f"{nodes:.1f} × 1.5", -(-nodes * 1.5 // 1))
show("  пам'ять на всі з'єднання", f"{conns:.0f} × {CONN_MEMORY_KB} КБ", conns * CONN_MEMORY_KB * KB / GB, "ГБ")
show("  heartbeat-пінгів/с (раз на 30 с)", f"{conns:.0f} / {HEARTBEAT_S}", conns / HEARTBEAT_S, "ping/s")

print("\n3. Сховище повідомлень за 2 роки")
total = show("  повідомлень за 2 роки", f"{per_day:,} × 365 × 2", per_day * 365 * 2)
raw = show("  сирий обсяг (200 Б на повідомлення)", f"{total / 1e9:.0f} млрд × {MSG_BYTES} Б", total * MSG_BYTES / TB, "ТБ")
repl = show("  × 3 репліки (RF = 3)", f"{raw:.1f} × {REPLICATION}", raw * REPLICATION, "ТБ")
disk = show("  + 30% місця під compaction", f"{repl:.1f} × {COMPACTION_HEADROOM}", repl * COMPACTION_HEADROOM, "ТБ")
show("  вузлів по 4 ТБ", f"{disk:.0f} / 4", -(-disk / 4 // 1))
show("  медіа окремо: 10% повідомлень × 300 КБ", f"{total / 1e9:.0f} млрд × 0.1 × 300 КБ",
     total * MEDIA_SHARE * MEDIA_KB * KB / PB, "ПБ (object storage)")

print("\n4. Fan-out presence для типового користувача")
online_contacts = show("  онлайн-контактів одночасно", f"{CONTACTS} × {ONLINE_SHARE}", CONTACTS * ONLINE_SHARE)
naive_user = show("  наївно: подій на користувача на добу", f"{TRANSITIONS} × {online_contacts:.0f}", TRANSITIONS * online_contacts)
naive_total = show("  наївно: подій на всіх на добу", f"{DAU:,} × {naive_user:.0f}", DAU * naive_user)
naive_qps = show("  наївно: подій/с", f"{naive_total / 1e9:.1f} млрд / {SECONDS_PER_DAY:,}", naive_total / SECONDS_PER_DAY, "events/s")
show("  у скільки разів більше, ніж повідомлень", f"{naive_qps:.0f} / {avg:.0f}", naive_qps / avg, "×")
opt_user = show("  з підпискою + grace 30 с: подій на користувача",
                f"{TRANSITIONS_AFTER_GRACE} × {SUBSCRIBERS}", TRANSITIONS_AFTER_GRACE * SUBSCRIBERS)
opt_qps = show("  оптимізовано: подій/с", f"{DAU:,} × {opt_user} / {SECONDS_PER_DAY:,}", DAU * opt_user / SECONDS_PER_DAY, "events/s")
show("  зменшення", f"{naive_qps:.0f} / {opt_qps:.0f}", naive_qps / opt_qps, "×")
show("  падіння 1 вузла Gateway: наївно offline-подій", f"{CONN_PER_NODE:,} × {online_contacts:.0f}", CONN_PER_NODE * online_contacts)
