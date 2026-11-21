from shop.models import Order
from shop.notifiers.base import Notifier


class EmailNotifier(Notifier):
    def notify(self, order: Order, message: str) -> None:
        print(f"Sending Email to {order.customer_email}: {message}")
