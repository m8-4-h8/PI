"""Захист від double-booking на PostgreSQL: 80 паралельних покупців -> 1 місце.

Наївний варіант «прочитав статус -> якщо вільне, записав» дає кілька переможців.
Умовний UPDATE (optimistic, з версією) + UNIQUE(event_id, seat_id) у квитках -- рівно одного.

BOOKING_DSN="dbname=... user=... password=... host=localhost" python double_booking_demo.py
"""
import os
import threading
import time
import uuid

import psycopg2

DSN = os.environ.get("BOOKING_DSN", "dbname=hotel user=lab password=lab host=localhost")
BUYERS = 80
EVENT, SEAT = 1, "A-1"

SCHEMA = """
DROP TABLE IF EXISTS tickets, seats, idempotency_keys;
CREATE TABLE seats (
    event_id     BIGINT NOT NULL,
    seat_id      TEXT   NOT NULL,
    status       TEXT   NOT NULL DEFAULT 'available',   -- available / held / sold
    holder       TEXT,
    hold_expires TIMESTAMPTZ,
    version      INT    NOT NULL DEFAULT 0,
    PRIMARY KEY (event_id, seat_id)
);
CREATE TABLE tickets (
    ticket_id  TEXT PRIMARY KEY,
    event_id   BIGINT NOT NULL,
    seat_id    TEXT   NOT NULL,
    buyer      TEXT   NOT NULL,
    UNIQUE (event_id, seat_id)                          -- остання лінія захисту
);
CREATE TABLE idempotency_keys (
    key        TEXT PRIMARY KEY,
    ticket_id  TEXT NOT NULL
);
"""


def reset():
    with psycopg2.connect(DSN) as db, db.cursor() as cur:
        cur.execute(SCHEMA)
        cur.execute("INSERT INTO seats (event_id, seat_id) VALUES (%s, %s)", (EVENT, SEAT))


def naive_hold(buyer, winners):
    """Check-then-act: вікно гонки між SELECT і UPDATE."""
    db = psycopg2.connect(DSN)
    try:
        with db, db.cursor() as cur:
            cur.execute("SELECT status FROM seats WHERE event_id = %s AND seat_id = %s", (EVENT, SEAT))
            if cur.fetchone()[0] == "available":
                time.sleep(0.01)                       # мережа, валідація, що завгодно
                cur.execute("UPDATE seats SET status = 'held', holder = %s WHERE event_id = %s AND seat_id = %s",
                            (buyer, EVENT, SEAT))
                winners.append(buyer)
    finally:
        db.close()


def safe_hold(buyer, winners):
    """Атомарний умовний UPDATE: перевірка і запис -- одна операція в базі."""
    db = psycopg2.connect(DSN)
    try:
        with db, db.cursor() as cur:
            cur.execute("""
                UPDATE seats
                   SET status = 'held', holder = %s, hold_expires = now() + interval '10 minutes',
                       version = version + 1
                 WHERE event_id = %s AND seat_id = %s AND status = 'available'
             RETURNING version""", (buyer, EVENT, SEAT))
            if cur.fetchone() is not None:
                winners.append(buyer)
    finally:
        db.close()


def buy(buyer, idempotency_key):
    """Оплата утриманого місця з Idempotency-Key: повтор не створює другий квиток."""
    with psycopg2.connect(DSN) as db, db.cursor() as cur:
        cur.execute("SELECT ticket_id FROM idempotency_keys WHERE key = %s", (idempotency_key,))
        row = cur.fetchone()
        if row:
            return row[0]
        ticket_id = f"tk_{uuid.uuid4().hex[:8]}"
        cur.execute("UPDATE seats SET status = 'sold' WHERE event_id = %s AND seat_id = %s "
                    "AND status = 'held' AND holder = %s", (EVENT, SEAT, buyer))
        if cur.rowcount != 1:
            raise RuntimeError("hold expired or belongs to another buyer")
        cur.execute("INSERT INTO tickets VALUES (%s, %s, %s, %s)", (ticket_id, EVENT, SEAT, buyer))
        cur.execute("INSERT INTO idempotency_keys VALUES (%s, %s)", (idempotency_key, ticket_id))
        return ticket_id


def race(fn):
    reset()
    winners, start = [], threading.Barrier(BUYERS)

    def worker(i):
        start.wait()
        fn(f"user-{i}", winners)
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(BUYERS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return winners


def main():
    naive = race(naive_hold)
    print(f"Наївний check-then-act: {BUYERS} покупців -> переможців: {len(naive)} (double-booking!)")
    safe = race(safe_hold)
    print(f"Умовний UPDATE ... WHERE status = 'available': {BUYERS} покупців -> переможців: {len(safe)}")

    winner = safe[0]
    key = str(uuid.uuid4())
    first, second = buy(winner, key), buy(winner, key)
    with psycopg2.connect(DSN) as db, db.cursor() as cur:
        cur.execute("SELECT count(*) FROM tickets WHERE event_id = %s AND seat_id = %s", (EVENT, SEAT))
        count = cur.fetchone()[0]
        try:
            cur.execute("INSERT INTO tickets VALUES ('tk_evil', %s, %s, 'user-x')", (EVENT, SEAT))
            unique = "НЕ спрацював"
        except psycopg2.errors.UniqueViolation:
            unique = "спрацював (UniqueViolation)"
    print(f"Оплата двічі з тим самим Idempotency-Key: {first} == {second} -> квитків на місце: {count}")
    print(f"Спроба вставити другий квиток на те саме місце в обхід логіки: UNIQUE {unique}")
    return len(naive), len(safe), count


if __name__ == "__main__":
    main()
