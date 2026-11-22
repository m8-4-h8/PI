"""Завдання 2. Retry з exponential backoff і full jitter."""
import random
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class TransientError(Exception):
    """Тимчасова помилка: тайм-аут, 503, розрив з'єднання. Лише її має сенс повторювати."""


def backoff_delay(attempt: int, base_delay: float, max_delay: float, rng: random.Random) -> float:
    """Full jitter: випадкове число від 0 до min(base_delay * 2^attempt, max_delay)."""
    cap = min(base_delay * 2 ** attempt, max_delay)
    return rng.uniform(0, cap)


def retry(fn: Callable[[], T], *, max_attempts: int = 4, base_delay: float = 0.1,
          max_delay: float = 2.0, sleep: Callable[[float], None] = time.sleep,
          rng: random.Random | None = None,
          on_retry: Callable[[int, float, Exception], None] | None = None) -> T:
    """Викликає fn; повторює лише при TransientError, не більше max_attempts спроб загалом."""
    rng = rng or random.Random()
    for attempt in range(max_attempts):
        try:
            return fn()
        except TransientError as error:
            if attempt == max_attempts - 1:
                raise
            delay = backoff_delay(attempt, base_delay, max_delay, rng)
            if on_retry:
                on_retry(attempt + 1, delay, error)
            sleep(delay)
    raise AssertionError("unreachable")
