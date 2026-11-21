from notifications.gateways.base import MessageGateway
from notifications.models import Order
from notifications.observers.base import OrderObserver
from notifications.retry.base import RetryStrategy


class PushObserver(OrderObserver):
    """Завдання 4: новий канал. Новий файл, наявні файли не змінювалися."""

    def __init__(self, gateway: MessageGateway, retry: RetryStrategy) -> None:
        self._gateway = gateway
        self._retry = retry

    def notify(self, order: Order) -> None:
        if order.customer.wants("push"):
            self._retry.send(self._send, order)

    def _send(self, order: Order) -> None:
        self._gateway.send(f"app-user:{order.customer.email}", f"order {order.id} confirmed")
