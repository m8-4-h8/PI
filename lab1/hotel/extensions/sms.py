from hotel.models import Booking
from hotel.notifiers.base import Notifier


class SmsNotifier(Notifier):
    """Завдання 3: SMS-підтвердження замість Email."""

    def notify(self, booking: Booking, message: str) -> None:
        print(f"Sending SMS to {booking.guest_phone}: {message}")
