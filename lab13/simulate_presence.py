"""Завдання 4(б): fan-out presence наївно vs з підпискою, grace period і coalescing.

Сценарій 1 — звичайна вечірня година: 5 000 користувачів, у кожного ~150 контактів,
сесії у фокусі ~3 хв, 65 % виходів у фон коротші за 30 с (перемкнувся в інший застосунок).
Сценарій 2 — масова зміна статусів: збій мережі в одній із трьох зон обриває 1/3 онлайн-з'єднань
з Connection Gateway одночасно; 95 % клієнтів перепідключаються з backoff + full jitter (0–30 с),
5 % не повертаються.

python simulate_presence.py   -> results/presence_simulation.txt
"""
import heapq
import random

from messenger.presence import NaivePresence, PresenceService

SEED = 13
USERS = 5_000
HALF_DEGREE = 75            # кожен додає 75 випадкових контактів -> у середньому ~150
VISIBLE_CHATS = 8           # скільки контактів видно в списку чатів на екрані
HORIZON = 3_600
P_SHORT_GAP = 0.65
ONLINE_SHARE = 0.3
ZONES = 3


def build_graph(rng: random.Random, users: int):
    contacts = {u: set() for u in range(users)}
    for u in range(users):
        for v in rng.sample(range(users), HALF_DEGREE):
            if v != u:
                contacts[u].add(v)
                contacts[v].add(u)
    contacts = {u: sorted(c) for u, c in contacts.items()}
    visible = {u: rng.sample(contacts[u], min(VISIBLE_CHATS, len(contacts[u]))) for u in range(users)}
    return contacts, visible


def replay(events, contacts, visible, initially_online, horizon):
    """Ті самі події з Connection Gateway подаються в обидві моделі."""
    naive, smart = NaivePresence(contacts), PresenceService()
    connected = set(initially_online)
    for u in initially_online:
        naive.connect(u, 0)
        smart.connect(u, 0)
    for u in initially_online:
        smart.subscribe(u, visible[u])
    smart.tick(0)
    base_naive, base_smart = naive.events, smart.events     # стартовий стан не рахуємо
    naive.timeline.clear()
    smart.timeline.clear()

    heapq.heapify(events)
    second = 1
    while events:
        t, _, u, kind, reason = heapq.heappop(events)
        if t > horizon:
            break
        while second <= t:
            smart.tick(second)
            second += 1
        if kind == "up" and u not in connected:
            connected.add(u)
            naive.connect(u, t)
            smart.connect(u, t)
            smart.subscribe(u, visible[u])
        elif kind == "down" and u in connected:
            connected.discard(u)
            naive.disconnect(u, t, reason)
            smart.disconnect(u, t, reason)
    while second <= horizon + 60:
        smart.tick(second)
        second += 1
    naive.events -= base_naive
    smart.events -= base_smart
    return naive, smart


def normal_hour(seed: int = SEED, users: int = USERS):
    rng = random.Random(seed)
    contacts, visible = build_graph(rng, users)
    events, seq, initially_online = [], 0, set()
    for u in range(users):
        t, online = 0.0, rng.random() < 0.2
        if online:
            initially_online.add(u)
        while t < HORIZON:
            if online:
                t += rng.expovariate(1 / 180)
                reason = "lost" if rng.random() < 0.05 else "background"
                events.append((t, seq, u, "down", reason))
            else:
                t += rng.uniform(3, 25) if rng.random() < P_SHORT_GAP else rng.expovariate(1 / 1_200)
                events.append((t, seq, u, "up", ""))
            seq += 1
            online = not online
    return replay(events, contacts, visible, initially_online, HORIZON) + (contacts,)


def zone_failure(seed: int = SEED, users: int = USERS):
    rng = random.Random(seed)
    contacts, visible = build_graph(rng, users)
    online = {u for u in range(users) if rng.random() < ONLINE_SHARE}
    victims = sorted(u for u in online if u % ZONES == 0)
    events, seq = [], 0
    for u in victims:
        events.append((1.0, seq, u, "down", "lost"))
        back = 1.0 + (rng.uniform(0, 30) if rng.random() < 0.95 else rng.uniform(120, 600))
        events.append((back, seq + 1, u, "up", ""))
        seq += 2
    naive, smart = replay(events, contacts, visible, online, horizon=120)
    return naive, smart, len(online), len(victims)


def row(label, a, b):
    return f"{label:<40}{a:>11,}  {b:>13,}".replace(",", " ")


def run(seed: int = SEED, users: int = USERS, quiet: bool = False):
    naive, smart, contacts = normal_hour(seed, users)
    f_naive, f_smart, online, victims = zone_failure(seed, users)
    avg_contacts = sum(len(c) for c in contacts.values()) / len(contacts)
    lines = [
        f"Користувачів: {users}, контактів у середньому: {avg_contacts:.0f}",
        "",
        f"Сценарій 1. Звичайна вечірня година ({HORIZON} с)",
        f"{'':<40}{'наївно':>11}  {'оптимізовано':>13}",
        row("Подій presence за годину", naive.events, smart.events),
        f"{'  на одного користувача':<40}{naive.events / users:>11.1f}  {smart.events / users:>13.1f}",
        f"{'  зменшення':<40}{'':>11}  {naive.events / smart.events:>12.1f}×",
        row("Пік подій за 1 секунду", max(naive.timeline.values()), max(smart.timeline.values())),
        f"WebSocket-кадрів з оновленнями (пачки за 2 с): {smart.frames}",
        f"Перепідключень у межах grace без жодної події: {smart.absorbed_flaps}",
        "",
        f"Сценарій 2. Збій однієї зони: онлайн {online}, обірвано {victims} з'єднань одночасно",
        f"{'':<40}{'наївно':>11}  {'оптимізовано':>13}",
        row("Подій presence за 120 с", f_naive.events, f_smart.events),
        row("Пік подій за 1 секунду", max(f_naive.timeline.values(), default=0),
            max(f_smart.timeline.values(), default=0)),
        f"Перепідключень у межах grace без жодної події: {f_smart.absorbed_flaps} з {victims}",
    ]
    if not quiet:
        print("\n".join(lines))
    return {"naive": naive.events, "smart": smart.events,
            "fail_naive": f_naive.events, "fail_smart": f_smart.events, "victims": victims,
            "absorbed": f_smart.absorbed_flaps}


if __name__ == "__main__":
    run()
