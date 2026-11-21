from notifications.models import Order
from notifications.observers.base import OrderObserver


class OrderService:
    """Subject: зберігає підписників і сповіщає їх, не знаючи, скільки каналів існує і які саме."""

    def __init__(self) -> None:
        self._observers: list[OrderObserver] = []

    def subscribe(self, observer: OrderObserver) -> None:
        self._observers.append(observer)

    def unsubscribe(self, observer: OrderObserver) -> None:
        self._observers.remove(observer)

    def place_order(self, order: Order) -> None:
        print(f"Saving order {order.id}...")
        for observer in self._observers:
            observer.notify(order)
