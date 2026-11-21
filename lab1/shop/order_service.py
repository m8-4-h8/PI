from collections.abc import Mapping

# Лише абстракції — жодної конкретної реалізації (DIP).
from shop.discounts.base import DiscountStrategy
from shop.models import Order
from shop.notifiers.base import Notifier
from shop.payments.base import PaymentProcessor
from shop.repositories.base import OrderRepository
from shop.validation import OrderValidator


class UnsupportedOptionError(KeyError):
    """Невідомий тип клієнта або спосіб оплати."""


class OrderService:
    """Координує обробку замовлення. Усі залежності приходять через конструктор."""

    def __init__(
        self,
        validator: OrderValidator,
        discounts: Mapping[str, DiscountStrategy],
        payments: Mapping[str, PaymentProcessor],
        repository: OrderRepository,
        notifier: Notifier,
    ) -> None:
        self._validator = validator
        self._discounts = dict(discounts)
        self._payments = dict(payments)
        self._repository = repository
        self._notifier = notifier

    def process_order(self, order: Order, payment_type: str) -> float:
        self._validator.validate(order)

        discount = self._lookup(self._discounts, order.customer_type, "customer type")
        payment = self._lookup(self._payments, payment_type, "payment type")

        total = discount.apply(order.subtotal)
        payment.pay(total)
        self._repository.save(order, total)
        self._notifier.notify(order, "Your order is processed.")
        return total

    @staticmethod
    def _lookup(options: Mapping, key: str, what: str):
        try:
            return options[key]
        except KeyError:
            raise UnsupportedOptionError(f"Unsupported {what}: {key!r}") from None
