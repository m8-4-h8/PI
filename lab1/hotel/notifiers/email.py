from hotel.models import Booking
from hotel.notifiers.base import Notifier


class EmailNotifier(Notifier):
    def notify(self, booking: Booking, message: str) -> None:
        print(f"Sending Email to {booking.guest_email}: {message}")
