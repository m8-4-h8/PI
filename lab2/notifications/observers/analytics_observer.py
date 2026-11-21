from notifications.models import Order
from notifications.observers.base import OrderObserver


class AnalyticsObserver(OrderObserver):
    """Журнал аналітики для внутрішньої команди — теж підписник, а не print у place_order."""

    def __init__(self) -> None:
        self.journal: list[str] = []

    def notify(self, order: Order) -> None:
        entry = f"[ANALYTICS] order {order.id} placed, total={order.total}"
        self.journal.append(entry)
        print(entry)
