from abc import ABC, abstractmethod

from hotel.models import Booking


class BookingValidationError(ValueError):
    """Бронювання не пройшло перевірку."""


class BookingValidator(ABC):
    @abstractmethod
    def validate(self, booking: Booking) -> None:
        """Кидає BookingValidationError, якщо бронювання некоректне."""


class HasRoomsValidator(BookingValidator):
    def validate(self, booking: Booking) -> None:
        if not booking.rooms:
            raise BookingValidationError("Booking has no rooms")
