from abc import ABC, abstractmethod
from collections.abc import Callable

from notifications.models import Order

Sender = Callable[[Order], None]


class RetryStrategy(ABC):
    """Як поводитися при збої надсилання. Повертає True, якщо повідомлення доставлено."""

    @abstractmethod
    def send(self, sender: Sender, order: Order) -> bool:
        ...
