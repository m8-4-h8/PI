from notifications.gateways.base import MessageGateway
from notifications.models import Booking
from notifications.observers.base import BookingObserver
from notifications.retry.base import RetryStrategy


class PushObserver(BookingObserver):
    """Завдання 4: новий канал. Новий файл, наявні файли не змінювалися."""

    def __init__(self, gateway: MessageGateway, retry: RetryStrategy) -> None:
        self._gateway = gateway
        self._retry = retry

    def notify(self, booking: Booking) -> None:
        if booking.guest.wants("push"):
            self._retry.send(self._send, booking)

    def _send(self, booking: Booking) -> None:
        self._gateway.send(f"app-user:{booking.guest.email}", f"booking {booking.id} confirmed")
