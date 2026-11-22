"""Завдання 4(а): перевірка дедуплікації в мережі, що губить запити, ACK і дублює доставки.

python simulate_dedup.py   -> results/dedup_simulation.txt
"""
import random

from messenger.dedup import Clock, Crash, DedupCache, Device, MessageService, MessageStore

SEED = 13
MESSAGES = 20_000
P_REQUEST_LOST = 0.08      # запит не дійшов до Message Service
P_CRASH_AFTER_CLAIM = 0.02
P_CRASH_AFTER_PERSIST = 0.03
P_ACK_LOST = 0.08          # записали, але ACK загубився дорогою назад
P_DELIVERY_DUP = 0.10      # Connection Gateway доставив двічі (повтор після reconnect)
P_DELIVERY_DROP = 0.05     # push загубився: отримувач добере через sync
ROUND_SECONDS = 3          # клієнт повторює неп-ACK-нуті повідомлення раз на ~3 с


def run(seed: int = SEED, messages: int = MESSAGES, flush_redis_at: float | None = 0.5, quiet: bool = False):
    rng = random.Random(seed)
    clock = Clock()
    store = MessageStore()
    cache = DedupCache(clock)
    faults = {"after_claim": P_CRASH_AFTER_CLAIM, "after_persist": P_CRASH_AFTER_PERSIST}
    service = MessageService(store, cache, clock, faults=lambda point: rng.random() < faults[point])

    users = 300
    devices = {u: Device(u, device_id=10_000 + u) for u in range(users)}
    conversations = {}
    for c in range(150):                      # 1-на-1
        a, b = rng.sample(range(users), 2)
        conversations[c] = [a, b]
    for c in range(150, 180):                 # групи 3–10 учасників
        conversations[c] = rng.sample(range(users), rng.randint(3, 10))

    in_flight = []                            # доставки, що ще в мережі

    def deliver(msg):                         # CDC -> Delivery Workers -> Connection Gateway
        for member in conversations[msg.conversation_id]:
            if member == msg.sender or rng.random() < P_DELIVERY_DROP:
                continue
            copies = 2 if rng.random() < P_DELIVERY_DUP else 1
            in_flight.extend([(member, msg)] * copies)

    store.on_append.append(deliver)

    attempts = arrived = acks_lost = 0
    crashes = {"after_claim": 0, "after_persist": 0}
    composed = 0
    flushed = False
    rounds = 0
    while True:
        rounds += 1
        for _ in range(min(500, messages - composed)):
            conv = rng.choice(list(conversations))
            sender = rng.choice(conversations[conv])
            devices[sender].compose(conv, f"text {composed}")
            composed += 1
        if flush_redis_at is not None and not flushed and composed >= messages * flush_redis_at:
            cache.flush()
            flushed = True
        pending = [(d, item) for d in devices.values() for item in d.pending()]
        if not pending and composed >= messages:
            break
        for device, item in pending:
            item.attempts += 1
            attempts += 1
            if rng.random() < P_REQUEST_LOST:
                continue
            arrived += 1
            try:
                ack = service.send(item.conversation_id, item.message_id, device.user_id, item.text, item.attempts)
            except Crash as crash:
                crashes[str(crash)] += 1
                continue
            if rng.random() < P_ACK_LOST:
                acks_lost += 1
                continue
            device.on_ack(ack)
        rng.shuffle(in_flight)                # доставки приходять не по порядку
        for member, msg in in_flight:
            devices[member].on_deliver(msg)
        in_flight.clear()
        for device in devices.values():       # пропуск за server_seq -> sync(conversation_id, last_seq)
            for conv in device.conversations_with_gaps():
                device.sync(store, conv)
        clock.advance(ROUND_SECONDS)

    gap_syncs = sum(d.stats.sync_requests for d in devices.values())
    final_syncs = 0
    for device in devices.values():           # reconnect: sync за курсором для кожної розмови
        for conv, members in conversations.items():
            if device.user_id in members:
                before = device.stats.recovered_by_sync
                device.sync(store, conv)
                final_syncs += device.stats.recovered_by_sync - before

    # Перевірка: у кожного учасника кожна розмова = 1..N без пропусків і повторів.
    ok = True
    for conv, members in conversations.items():
        expected = [m.server_seq for m in store.read_after(conv, 0)]
        for member in members:
            got = [m.server_seq for m in devices[member].timeline.get(conv, [])]
            ids = [m.message_id for m in devices[member].timeline.get(conv, [])]
            if got != expected or len(ids) != len(set(ids)):
                ok = False

    received = sum(d.stats.received for d in devices.values())
    dropped = sum(d.stats.duplicates_dropped for d in devices.values())
    gaps = sum(d.stats.gaps_detected for d in devices.values())
    recovered = sum(d.stats.recovered_by_sync for d in devices.values())
    st = service.stats
    lines = [
        f"Повідомлень створено на пристроях:              {composed}",
        f"Спроб надсилання (з повторами):                {attempts}",
        f"  з них дійшли до Message Service:             {arrived}",
        f"  інстанс упав після claim, до запису:         {crashes['after_claim']}",
        f"  інстанс упав після запису, до ACK:           {crashes['after_persist']}",
        f"  ACK загубився на зворотному шляху:           {acks_lost}",
        f"Redis очищено (failover) посеред прогону:      {'так' if flushed else 'ні'}",
        "",
        f"Без дедуплікації рядків у Message Store було б: {arrived - crashes['after_claim']}",
        f"З дедуплікацією рядків у Message Store:         {store.row_count()}",
        f"  записано нових:                               {st.new}",
        f"  дубль знайдено в Redis:                       {st.dup_from_cache}",
        f"  дубль знайдено в msg_by_client_id (після flush чи crash): {st.dup_from_store}",
        f"  відповідь «in progress» (живий pending):       {st.in_progress}",
        f"  перехоплено протермінований pending:          {st.took_over_stale}",
        "",
        f"Доставок отримувачам (з дублями):              {received}",
        f"  відкинуто дублів за message_id:              {dropped}",
        f"  пропусків за server_seq (буферизовано):       {gaps}",
        f"  запитів sync через пропуск:                  {gap_syncs}",
        f"  повідомлень дібрано через sync:              {recovered}",
        f"  з них лише фінальним sync після reconnect:   {final_syncs}",
        f"Кожен учасник бачить кожну розмову рівно 1..N, без повторів: {'ТАК' if ok else 'НІ'}",
    ]
    if not quiet:
        print("\n".join(lines))
    return {"ok": ok, "rows": store.row_count(), "composed": composed, "stats": st,
            "arrived": arrived, "crashes": crashes, "dropped": dropped, "final_syncs": final_syncs}


if __name__ == "__main__":
    run()
