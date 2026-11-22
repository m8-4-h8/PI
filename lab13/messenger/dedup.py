"""Завдання 4(а). Дедуплікація повідомлень на трьох рівнях.

1. Відправник: message_id генерується на пристрої ДО першої спроби і зберігається в outbox.
   Кожен повтор іде з тим самим message_id і з лічильником спроб `attempt`.
2. Message Service: швидка перевірка в Redis (`SET dedup:{conv}:{id} NX EX 86400`) і
   надійна перевірка в Message Store (таблиця msg_by_client_id) — лише для повторів (attempt > 1).
3. Отримувач: унікальний індекс за message_id у локальній БД + курсор last_seq на розмову.

Доставка всюди at-least-once, а «рівно один раз» бачить лише користувач — завдяки цим трьом перевіркам.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True, order=True)
class MessageId:
    """128 біт: device_id (видає сервер при реєстрації пристрою) + client_seq (лічильник пристрою)."""

    device_id: int
    client_seq: int

    def __str__(self) -> str:
        return f"{self.device_id:016x}-{self.client_seq:016x}"


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def advance(self, seconds: float) -> None:
        self.now += seconds


class Crash(Exception):
    """Інстанс Message Service впав посеред обробки — клієнт не отримав ACK."""


class DedupCache:
    """Модель Redis: SET NX EX, GET, SET. `flush()` — failover без реплікації (усе втрачено)."""

    def __init__(self, clock: Clock, ttl: float = 86_400) -> None:
        self._clock, self._ttl = clock, ttl
        self._data: dict[str, tuple[object, float]] = {}

    def get(self, key: str):
        item = self._data.get(key)
        if item is None or item[1] <= self._clock.now:
            return None
        return item[0]

    def set_nx(self, key: str, value) -> bool:
        if self.get(key) is not None:
            return False
        self.set(key, value)
        return True

    def set(self, key: str, value) -> None:
        self._data[key] = (value, self._clock.now + self._ttl)

    def flush(self) -> None:
        self._data.clear()


@dataclass(frozen=True)
class StoredMessage:
    conversation_id: int
    server_seq: int
    message_id: MessageId
    sender: int
    text: str


class MessageStore:
    """Модель Cassandra.

    messages          PRIMARY KEY ((conversation_id, month), server_seq)
    msg_by_client_id  PRIMARY KEY ((conversation_id), message_id) -> server_seq
    Обидві таблиці пишуться одним logged batch. Підписники `on_append` — це CDC (Debezium/Kafka):
    доставку запускає факт запису, а не код сервісу, тому падіння після запису не губить доставку.
    """

    def __init__(self) -> None:
        self.messages: dict[int, dict[int, StoredMessage]] = {}
        self._by_client_id: dict[tuple[int, MessageId], int] = {}
        self._counters: dict[int, int] = {}
        self.on_append: list[Callable[[StoredMessage], None]] = []

    def append(self, conversation_id: int, message_id: MessageId, sender: int, text: str) -> int:
        # У проді seq видає Redis INCR seq:{conversation_id}; він монотонний, пропуски допустимі.
        seq = self._counters.get(conversation_id, 0) + 1
        self._counters[conversation_id] = seq
        msg = StoredMessage(conversation_id, seq, message_id, sender, text)
        self.messages.setdefault(conversation_id, {})[seq] = msg
        self._by_client_id[(conversation_id, message_id)] = seq
        for listener in self.on_append:
            listener(msg)
        return seq

    def lookup(self, conversation_id: int, message_id: MessageId) -> int | None:
        return self._by_client_id.get((conversation_id, message_id))

    def read_after(self, conversation_id: int, after_seq: int) -> list[StoredMessage]:
        rows = self.messages.get(conversation_id, {})
        return [rows[s] for s in sorted(rows) if s > after_seq]

    def row_count(self) -> int:
        return sum(len(rows) for rows in self.messages.values())


@dataclass
class Ack:
    message_id: MessageId
    server_seq: int | None
    duplicate: bool = False
    in_progress: bool = False


@dataclass
class DedupStats:
    new: int = 0
    dup_from_cache: int = 0
    dup_from_store: int = 0
    in_progress: int = 0
    took_over_stale: int = 0


class MessageService:
    """Обробка `send` від Connection Gateway. Кроки пронумеровано так само, як у README."""

    LEASE = 10.0  # скільки секунд «pending» вважається живим

    def __init__(self, store: MessageStore, cache: DedupCache, clock: Clock,
                 faults: Callable[[str], bool] | None = None) -> None:
        self.store, self.cache, self.clock = store, cache, clock
        self._faults = faults or (lambda point: False)
        self.stats = DedupStats()

    def send(self, conversation_id: int, message_id: MessageId, sender: int, text: str,
             attempt: int) -> Ack:
        key = f"dedup:{conversation_id}:{message_id}"
        # 1. Швидка перевірка в Redis.
        hit = self.cache.get(key)
        if hit is not None and hit[0] == "done":
            self.stats.dup_from_cache += 1
            return Ack(message_id, hit[1], duplicate=True)
        if hit is not None and self.clock.now - hit[1] < self.LEASE:
            self.stats.in_progress += 1
            return Ack(message_id, None, in_progress=True)
        # 2. Надійна перевірка — лише для повторів: перша спроба не може бути дублем.
        if attempt > 1:
            seq = self.store.lookup(conversation_id, message_id)
            if seq is not None:
                self.cache.set(key, ("done", seq))
                self.stats.dup_from_store += 1
                return Ack(message_id, seq, duplicate=True)
        # 3. Захоплюємо обробку. Протермінований pending (попередній інстанс упав) — перехоплюємо.
        if hit is None:
            if not self.cache.set_nx(key, ("pending", self.clock.now)):
                self.stats.in_progress += 1
                return Ack(message_id, None, in_progress=True)
        else:
            self.stats.took_over_stale += 1
            self.cache.set(key, ("pending", self.clock.now))
        if self._faults("after_claim"):
            raise Crash("after_claim")
        # 4. Запис у Message Store (logged batch: messages + msg_by_client_id). CDC запускає доставку.
        seq = self.store.append(conversation_id, message_id, sender, text)
        self.stats.new += 1
        if self._faults("after_persist"):
            raise Crash("after_persist")
        # 5. Позначаємо як виконане і відповідаємо ACK («одна галочка»).
        self.cache.set(key, ("done", seq))
        return Ack(message_id, seq)


@dataclass
class OutboxItem:
    conversation_id: int
    message_id: MessageId
    text: str
    attempts: int = 0
    acked_seq: int | None = None


@dataclass
class DeviceStats:
    received: int = 0
    sync_requests: int = 0
    duplicates_dropped: int = 0
    gaps_detected: int = 0
    recovered_by_sync: int = 0


class Device:
    """Клієнтський пристрій.

    Відправка: outbox у локальній SQLite; message_id створюється до першої спроби, повтор —
    той самий message_id і attempt + 1.
    Отримання: локальна БД з UNIQUE(message_id) і курсором last_seq на розмову; показуємо
    строго за server_seq, пропуск -> sync(conversation_id, last_seq).
    """

    def __init__(self, user_id: int, device_id: int) -> None:
        self.user_id, self.device_id = user_id, device_id
        self._next_seq = 0
        self.outbox: dict[MessageId, OutboxItem] = {}
        self.seen: set[MessageId] = set()
        self.last_seq: dict[int, int] = {}
        self.buffered: dict[int, dict[int, StoredMessage]] = {}
        self.timeline: dict[int, list[StoredMessage]] = {}
        self.stats = DeviceStats()

    # --- відправка ---
    def compose(self, conversation_id: int, text: str) -> OutboxItem:
        self._next_seq += 1
        item = OutboxItem(conversation_id, MessageId(self.device_id, self._next_seq), text)
        self.outbox[item.message_id] = item   # спершу записали локально, потім шлемо
        return item

    def pending(self) -> list[OutboxItem]:
        return [i for i in self.outbox.values() if i.acked_seq is None]

    def on_ack(self, ack: Ack) -> None:
        if ack.server_seq is None:
            return
        item = self.outbox[ack.message_id]
        item.acked_seq = ack.server_seq
        own = StoredMessage(item.conversation_id, ack.server_seq, item.message_id, self.user_id, item.text)
        self._accept(own)

    # --- отримання ---
    def on_deliver(self, msg: StoredMessage) -> str:
        self.stats.received += 1
        return self._accept(msg)

    def sync(self, store: MessageStore, conversation_id: int) -> None:
        """Після reconnect чи пропуску: «дай усе після last_seq»."""
        self.stats.sync_requests += 1
        for msg in store.read_after(conversation_id, self.last_seq.get(conversation_id, 0)):
            if msg.message_id not in self.seen:
                self.stats.recovered_by_sync += 1
                self._show(msg)
        self.buffered.pop(conversation_id, None)

    def conversations_with_gaps(self) -> list[int]:
        return [conv for conv, buf in self.buffered.items() if buf]

    def _accept(self, msg: StoredMessage) -> str:
        buf = self.buffered.get(msg.conversation_id, {})
        if msg.message_id in self.seen or msg.server_seq in buf:
            self.stats.duplicates_dropped += 1
            return "duplicate"
        last = self.last_seq.get(msg.conversation_id, 0)
        if msg.server_seq > last + 1:
            self.buffered.setdefault(msg.conversation_id, {})[msg.server_seq] = msg
            self.stats.gaps_detected += 1
            return "gap"
        self._show(msg)
        self._drain(msg.conversation_id)
        return "shown"

    def _show(self, msg: StoredMessage) -> None:
        self.seen.add(msg.message_id)
        self.last_seq[msg.conversation_id] = msg.server_seq
        self.timeline.setdefault(msg.conversation_id, []).append(msg)

    def _drain(self, conversation_id: int) -> None:
        buf = self.buffered.get(conversation_id, {})
        nxt = self.last_seq[conversation_id] + 1
        while nxt in buf:
            self._show(buf.pop(nxt))
            nxt += 1
