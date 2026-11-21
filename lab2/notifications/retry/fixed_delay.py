import time
from collections.abc import Callable

from notifications.models import Booking
from notifications.retry.base import RetryStrategy, Sender


class FixedDelayStrategy(RetryStrategy):
    """Завдання 4: однакова пауза між спробами, без експоненційного зростання."""

    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._max_attempts = max_attempts
        self._delay = delay
        self._sleep = sleep

    def send(self, sender: Sender, booking: Booking) -> bool:
        for attempt in range(1, self._max_attempts + 1):
            try:
                sender(booking)
                return True
            except ConnectionError as error:
                if attempt == self._max_attempts:
                    print(f"  [fixed-delay] booking {booking.id}: gave up after {attempt} attempts ({error})")
                    return False
                print(f"  [fixed-delay] booking {booking.id}: attempt {attempt} failed, waiting {self._delay:.1f}s")
                self._sleep(self._delay)
        return False
