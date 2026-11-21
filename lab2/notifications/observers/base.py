from abc import ABC, abstractmethod

from notifications.models import Order


class OrderObserver(ABC):
    @abstractmethod
    def notify(self, order: Order) -> None:
        ...
