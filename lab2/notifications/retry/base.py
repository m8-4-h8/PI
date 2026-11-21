from abc import ABC, abstractmethod
from collections.abc import Callable

from notifications.models import Booking

Sender = Callable[[Booking], None]


class RetryStrategy(ABC):
    """Як поводитися при збої надсилання. Повертає True, якщо повідомлення доставлено."""

    @abstractmethod
    def send(self, sender: Sender, booking: Booking) -> bool:
        ...
