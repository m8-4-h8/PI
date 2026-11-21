from notifications.gateways.base import MessageGateway
from notifications.models import Booking
from notifications.observers.base import BookingObserver
from notifications.retry.base import RetryStrategy


class SmsObserver(BookingObserver):
    def __init__(self, gateway: MessageGateway, retry: RetryStrategy) -> None:
        self._gateway = gateway
        self._retry = retry

    def notify(self, booking: Booking) -> None:
        if booking.guest.wants("sms"):
            self._retry.send(self._send, booking)

    def _send(self, booking: Booking) -> None:
        self._gateway.send(booking.guest.phone, f"booking {booking.id} confirmed")
