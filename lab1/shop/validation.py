from abc import ABC, abstractmethod

from shop.models import Order


class OrderValidationError(ValueError):
    """Замовлення не пройшло перевірку."""


class OrderValidator(ABC):
    @abstractmethod
    def validate(self, order: Order) -> None:
        """Кидає OrderValidationError, якщо замовлення некоректне."""


class NonEmptyOrderValidator(OrderValidator):
    def validate(self, order: Order) -> None:
        if not order.items:
            raise OrderValidationError("Order is empty")
