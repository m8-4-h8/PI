from abc import ABC, abstractmethod

from shop.models import Order


class Notifier(ABC):
    @abstractmethod
    def notify(self, order: Order, message: str) -> None:
        """Повідомити клієнта про результат обробки замовлення."""
