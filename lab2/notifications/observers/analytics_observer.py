from notifications.models import Booking
from notifications.observers.base import BookingObserver


class AnalyticsObserver(BookingObserver):
    """Журнал аналітики для внутрішньої команди — теж підписник, а не print у place_booking."""

    def __init__(self) -> None:
        self.journal: list[str] = []

    def notify(self, booking: Booking) -> None:
        entry = f"[ANALYTICS] booking {booking.id} placed, total={booking.total}"
        self.journal.append(entry)
        print(entry)
