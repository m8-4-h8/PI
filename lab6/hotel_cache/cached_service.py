"""Cache-aside над SlowRoomAvailabilityService. Увесь код кешування живе тут."""
import time
from collections import OrderedDict
from collections.abc import Callable


class TtlCache:
    """Словник з TTL для кожного запису і LRU-витісненням при переповненні."""

    def __init__(self, ttl_seconds: float, max_size: int = 10_000,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._clock = clock
        self._data: OrderedDict[str, tuple[float, object]] = OrderedDict()

    def get(self, key: str):
        entry = self._data.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if self._clock() >= expires_at:      # запис прострочений
            del self._data[key]
            return None
        self._data.move_to_end(key)          # LRU: нещодавно використаний
        return value

    def set(self, key: str, value) -> None:
        self._data[key] = (self._clock() + self._ttl, value)
        self._data.move_to_end(key)
        while len(self._data) > self._max_size:
            self._data.popitem(last=False)   # витісняємо найдавніше використаний

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def __len__(self) -> int:
        return len(self._data)


class CachedRoomAvailabilityService:
    """Cache-aside: спочатку кеш, при промаху -- база, потім запис у кеш."""

    DEFAULT_TTL_SECONDS = 30

    def __init__(self, backend, cache: TtlCache | None = None) -> None:
        self._backend = backend
        self._cache = cache if cache is not None else TtlCache(self.DEFAULT_TTL_SECONDS)
        self.hits = 0
        self.misses = 0

    def get_room(self, room_id: str) -> dict:
        cached = self._cache.get(room_id)
        if cached is not None:               # cache hit -- у базу не йдемо
            self.hits += 1
            return cached
        self.misses += 1                     # cache miss
        room = self._backend.get_room(room_id)
        if room is not None:
            self._cache.set(room_id, room)
        return room

    def invalidate(self, room_id: str) -> None:
        """Активна інвалідація: викликати після зміни ціни/доступності в адмінці."""
        self._cache.delete(room_id)
