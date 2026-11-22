"""Тести Cache-aside. Запуск: python test_cache.py (або pytest)."""
from hotel_cache.cached_service import CachedRoomAvailabilityService, TtlCache


class FakeBackend:
    def __init__(self):
        self.db_calls = 0
        self.prices = {"room-1": 1000}

    def get_room(self, room_id):
        self.db_calls += 1
        if room_id not in self.prices:
            return None
        return {"id": room_id, "price_per_night": self.prices[room_id]}


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def make(ttl=30, max_size=100):
    clock, backend = FakeClock(), FakeBackend()
    return clock, backend, CachedRoomAvailabilityService(backend, TtlCache(ttl, max_size, clock))


def test_miss_then_hit_does_not_call_backend_again():
    _, backend, service = make()
    assert service.get_room("room-1")["price_per_night"] == 1000
    assert service.get_room("room-1")["price_per_night"] == 1000
    assert backend.db_calls == 1 and (service.hits, service.misses) == (1, 1)


def test_entry_expires_after_ttl():
    clock, backend, service = make(ttl=30)
    service.get_room("room-1")
    clock.now = 29.9
    service.get_room("room-1")
    assert backend.db_calls == 1
    clock.now = 30.0
    service.get_room("room-1")
    assert backend.db_calls == 2


def test_stale_price_until_invalidation():
    _, backend, service = make()
    service.get_room("room-1")
    backend.prices["room-1"] = 1500                       # ціну змінили в адмінці
    assert service.get_room("room-1")["price_per_night"] == 1000   # застаріла ціна з кешу
    service.invalidate("room-1")
    assert service.get_room("room-1")["price_per_night"] == 1500


def test_missing_room_is_not_cached():
    _, backend, service = make()
    assert service.get_room("room-404") is None
    assert service.get_room("room-404") is None
    assert backend.db_calls == 2


def test_lru_eviction_when_cache_is_full():
    cache = TtlCache(ttl_seconds=100, max_size=2, clock=FakeClock())
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")          # a -- нещодавно використаний
    cache.set("c", 3)       # витісняється b
    assert cache.get("b") is None and cache.get("a") == 1 and cache.get("c") == 3


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for name, fn in tests:
        fn()
        print(f"ok  {name}")
    print(f"all {len(tests)} tests passed")
