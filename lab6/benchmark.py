"""Бенчмарк: 500 запитів, 80% -- на 10 «гарячих» номерів, 20% -- рівномірно на інші 40."""
import random
import time

from hotel_cache.cached_service import CachedRoomAvailabilityService
from hotel_cache.room_availability_service import SlowRoomAvailabilityService

N_REQUESTS = 500
SEED = 42


def make_requests(n: int, seed: int) -> list[str]:
    rnd = random.Random(seed)
    hot = [f"room-{i}" for i in range(1, 11)]
    cold = [f"room-{i}" for i in range(11, 51)]
    return [rnd.choice(hot) if rnd.random() < 0.8 else rnd.choice(cold) for _ in range(n)]


def run(service, requests) -> float:
    start = time.perf_counter()
    for room_id in requests:
        service.get_room(room_id)
    return time.perf_counter() - start


def main() -> None:
    requests = make_requests(N_REQUESTS, SEED)

    direct = SlowRoomAvailabilityService()
    t_direct = run(direct, requests)

    backend = SlowRoomAvailabilityService()
    cached = CachedRoomAvailabilityService(backend)
    t_cached = run(cached, requests)

    print(f"Запитів: {N_REQUESTS}, унікальних номерів у послідовності: {len(set(requests))}")
    print(f"{'Варіант':<30}{'Час, с':>10}{'Сер. затримка, мс':>20}{'db_calls':>10}")
    print(f"{'SlowRoomAvailabilityService':<30}{t_direct:>10.2f}{t_direct / N_REQUESTS * 1000:>20.2f}{direct.db_calls:>10}")
    print(f"{'CachedRoomAvailabilityService':<30}{t_cached:>10.2f}{t_cached / N_REQUESTS * 1000:>20.2f}{backend.db_calls:>10}")
    print(f"Cache hits: {cached.hits}, misses: {cached.misses}, hit ratio: {cached.hits / N_REQUESTS:.1%}")
    print(f"Прискорення: x{t_direct / t_cached:.1f}, навантаження на БД менше в x{direct.db_calls / backend.db_calls:.1f}")


if __name__ == "__main__":
    main()
