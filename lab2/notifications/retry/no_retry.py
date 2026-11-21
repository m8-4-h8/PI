from notifications.models import Booking
from notifications.retry.base import RetryStrategy, Sender


class NoRetryStrategy(RetryStrategy):
    """Для SMS: кожна спроба коштує грошей провайдеру, тому лише одна спроба."""

    def send(self, sender: Sender, booking: Booking) -> bool:
        try:
            sender(booking)
            return True
        except ConnectionError as error:
            print(f"  [no-retry] booking {booking.id}: failed once, not retrying ({error})")
            return False
