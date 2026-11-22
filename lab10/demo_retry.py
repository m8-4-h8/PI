"""Завдання 2. Сервіс падає перші 3 рази і відновлюється на 4-й спробі. Друкуємо реальні затримки."""
import time

from resilience.retry import TransientError, retry


class FlakyRoomInventory:
    def __init__(self, fail_times: int) -> None:
        self.fail_times = fail_times
        self.calls = 0

    def get_availability(self) -> dict:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise TransientError(f"503 Service Unavailable (виклик {self.calls})")
        return {"room_type": "double", "free": 3}


def run_once(label: str) -> None:
    service = FlakyRoomInventory(fail_times=3)
    last = time.perf_counter()

    def on_retry(attempt, delay, error):
        print(f"  спроба {attempt}: {error}; full jitter -> чекаємо {delay * 1000:6.1f} мс "
              f"(межа {min(0.1 * 2 ** (attempt - 1), 1.0) * 1000:.0f} мс)")

    start = time.perf_counter()
    result = retry(service.get_availability, max_attempts=5, base_delay=0.1, max_delay=1.0, on_retry=on_retry)
    print(f"  спроба {service.calls}: успіх {result}; разом {(time.perf_counter() - start) * 1000:.0f} мс")


if __name__ == "__main__":
    for run in (1, 2, 3):
        print(f"Прогін {run}:")
        run_once(str(run))
