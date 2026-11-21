import time
from collections.abc import Callable

from notifications.models import Order
from notifications.retry.base import RetryStrategy, Sender


class ExponentialBackoffStrategy(RetryStrategy):
    """Для Email: лист може почекати, тому повторюємо з паузою base, 2·base, 4·base…"""

    def __init__(
        self,
        max_attempts: int = 4,
        base_delay: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._sleep = sleep

    def send(self, sender: Sender, order: Order) -> bool:
        for attempt in range(1, self._max_attempts + 1):
            try:
                sender(order)
                return True
            except ConnectionError as error:
                if attempt == self._max_attempts:
                    print(f"  [retry] order {order.id}: gave up after {attempt} attempts ({error})")
                    return False
                delay = self._base_delay * 2 ** (attempt - 1)
                print(f"  [retry] order {order.id}: attempt {attempt} failed, waiting {delay:.1f}s")
                self._sleep(delay)
        return False
