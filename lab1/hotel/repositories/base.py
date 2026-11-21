from abc import ABC, abstractmethod

from hotel.models import Booking


class BookingRepository(ABC):
    @abstractmethod
    def save(self, booking: Booking, total: float) -> None:
        """Зберегти бронювання разом із підсумковою сумою."""
