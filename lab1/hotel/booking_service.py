from collections.abc import Mapping

# Лише абстракції — жодної конкретної реалізації (DIP).
from hotel.discounts.base import DiscountStrategy
from hotel.models import Booking
from hotel.notifiers.base import Notifier
from hotel.payments.base import PaymentProcessor
from hotel.repositories.base import BookingRepository
from hotel.validation import BookingValidator


class UnsupportedOptionError(KeyError):
    """Невідомий тип гостя або спосіб оплати."""


class HotelBookingService:
    """Координує обробку бронювання. Усі залежності приходять через конструктор."""

    def __init__(
        self,
        validator: BookingValidator,
        discounts: Mapping[str, DiscountStrategy],
        payments: Mapping[str, PaymentProcessor],
        repository: BookingRepository,
        notifier: Notifier,
    ) -> None:
        self._validator = validator
        self._discounts = dict(discounts)
        self._payments = dict(payments)
        self._repository = repository
        self._notifier = notifier

    def process_booking(self, booking: Booking, payment_type: str) -> float:
        self._validator.validate(booking)

        discount = self._lookup(self._discounts, booking.guest_type, "guest type")
        payment = self._lookup(self._payments, payment_type, "payment type")

        total = discount.apply(booking.subtotal)
        payment.pay(total)
        self._repository.save(booking, total)
        self._notifier.notify(booking, "Your booking is confirmed.")
        return total

    @staticmethod
    def _lookup(options: Mapping, key: str, what: str):
        try:
            return options[key]
        except KeyError:
            raise UnsupportedOptionError(f"Unsupported {what}: {key!r}") from None
