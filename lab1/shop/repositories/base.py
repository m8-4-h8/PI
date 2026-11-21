from abc import ABC, abstractmethod

from shop.models import Order


class OrderRepository(ABC):
    @abstractmethod
    def save(self, order: Order, total: float) -> None:
        """Зберегти замовлення разом із підсумковою сумою."""
