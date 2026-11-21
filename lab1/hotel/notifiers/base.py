from abc import ABC, abstractmethod

from hotel.models import Booking


class Notifier(ABC):
    @abstractmethod
    def notify(self, booking: Booking, message: str) -> None:
        """Повідомити гостя про результат бронювання."""
