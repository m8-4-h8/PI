from abc import ABC, abstractmethod

from notifications.models import Booking


class BookingObserver(ABC):
    @abstractmethod
    def notify(self, booking: Booking) -> None:
        ...
