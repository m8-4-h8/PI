"""Завдання 4(б). Presence Service: як обмежити fan-out при масовій зміні статусів.

Наївно: кожна зміна online/offline одразу розсилається всім онлайн-контактам.
Оптимізовано — чотири механізми:
1. Підписка, а не розсилка всім: статус отримують лише ті, у кого цей контакт зараз на екрані
   (відкритий чат або видимий список чатів), не більше MAX_SUBSCRIPTIONS на глядача.
2. Grace period для offline: короткий вихід у фон (< 30 с) чи обрив з'єднання (< 60 с) з
   подальшим reconnect не породжує жодної події. Last seen ставиться на час відключення.
3. Coalescing: події для одного глядача накопичуються у вікні BATCH_WINDOW і надсилаються одним
   кадром; для пари (глядач, контакт) лишається тільки останній стан.
4. У великих групах (> 100 учасників) per-user presence не розсилається: лише лічильник «N онлайн»
   за запитом (див. README).
"""
from __future__ import annotations

from collections import defaultdict

GRACE = {"logout": 0.0, "background": 30.0, "lost": 60.0}
BATCH_WINDOW = 2.0
MAX_SUBSCRIPTIONS = 20


class NaivePresence:
    def __init__(self, contacts: dict[int, list[int]]) -> None:
        self._contacts = contacts
        self.online: set[int] = set()
        self.events = 0
        self.timeline: dict[int, int] = defaultdict(int)   # секунда -> подій

    def connect(self, user: int, now: float) -> None:
        self.online.add(user)
        self._fanout(user, now)

    def disconnect(self, user: int, now: float, reason: str) -> None:
        self.online.discard(user)
        self._fanout(user, now)

    def _fanout(self, user: int, now: float) -> None:
        n = sum(1 for c in self._contacts[user] if c in self.online)
        self.events += n
        self.timeline[int(now)] += n


class PresenceService:
    def __init__(self) -> None:
        self.connected: set[int] = set()          # стан з'єднань від Connection Gateway
        self.visible: dict[int, str] = {}         # що бачать інші: online / offline
        self.last_seen: dict[int, float] = {}
        self._pending_offline: dict[int, tuple[float, float]] = {}   # user -> (deadline, disconnected_at)
        self._subscribers: dict[int, set[int]] = defaultdict(set)    # target -> viewers
        self._subscriptions: dict[int, set[int]] = defaultdict(set)  # viewer -> targets
        self._batch: dict[int, dict[int, str]] = defaultdict(dict)   # viewer -> {target: state}
        self._next_flush = BATCH_WINDOW
        self.events = 0              # оновлень статусу, доставлених глядачам
        self.frames = 0              # WebSocket-кадрів (один кадр = пачка для одного глядача)
        self.snapshot_reads = 0      # початковий стан при підписці (один запит на екран)
        self.absorbed_flaps = 0      # reconnect у межах grace — нічого не розсилали
        self.timeline: dict[int, int] = defaultdict(int)

    # --- підписки: клієнт повідомляє, чиї статуси зараз на екрані ---
    def subscribe(self, viewer: int, targets: list[int]) -> dict[int, str]:
        targets = targets[:MAX_SUBSCRIPTIONS]
        for t in targets:
            self._subscribers[t].add(viewer)
            self._subscriptions[viewer].add(t)
        self.snapshot_reads += 1
        return {t: self.visible.get(t, "offline") for t in targets}

    def unsubscribe_all(self, viewer: int) -> None:
        for t in self._subscriptions.pop(viewer, set()):
            self._subscribers[t].discard(viewer)
        self._batch.pop(viewer, None)

    # --- події від Connection Gateway ---
    def connect(self, user: int, now: float) -> None:
        self.connected.add(user)
        if self._pending_offline.pop(user, None) is not None:
            self.absorbed_flaps += 1      # повернувся в межах grace: для інших нічого не змінилось
            return
        if self.visible.get(user) != "online":
            self.visible[user] = "online"
            self._enqueue(user, "online")

    def disconnect(self, user: int, now: float, reason: str) -> None:
        self.connected.discard(user)
        self.unsubscribe_all(user)
        self._pending_offline[user] = (now + GRACE[reason], now)

    def tick(self, now: float) -> None:
        for user, (deadline, gone_at) in list(self._pending_offline.items()):
            if deadline <= now:
                del self._pending_offline[user]
                self.visible[user] = "offline"
                self.last_seen[user] = gone_at    # last seen — час відключення, а не кінця grace
                self._enqueue(user, "offline")
        if now >= self._next_flush:
            self._flush(now)
            self._next_flush = now + BATCH_WINDOW

    def _enqueue(self, target: int, state: str) -> None:
        for viewer in self._subscribers.get(target, ()):
            self._batch[viewer][target] = state   # перезапис = coalescing

    def _flush(self, now: float) -> None:
        for viewer, updates in self._batch.items():
            if updates:
                self.frames += 1
                self.events += len(updates)
                self.timeline[int(now)] += len(updates)
        self._batch.clear()
