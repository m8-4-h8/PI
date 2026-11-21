from notifications.gateways.base import MessageGateway
from notifications.models import Order
from notifications.observers.base import OrderObserver
from notifications.retry.base import RetryStrategy


class EmailObserver(OrderObserver):
    def __init__(self, gateway: MessageGateway, retry: RetryStrategy) -> None:
        self._gateway = gateway
        self._retry = retry

    def notify(self, order: Order) -> None:
        if order.customer.wants("email"):
            self._retry.send(self._send, order)

    def _send(self, order: Order) -> None:
        self._gateway.send(order.customer.email, f"order {order.id} confirmed")
