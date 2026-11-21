from shop.models import Order
from shop.notifiers.base import Notifier


class SmsNotifier(Notifier):
    """Завдання 3: SMS-нотифікація замість Email."""

    def notify(self, order: Order, message: str) -> None:
        print(f"Sending SMS to {order.customer_phone}: {message}")
