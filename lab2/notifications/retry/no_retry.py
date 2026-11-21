from notifications.models import Order
from notifications.retry.base import RetryStrategy, Sender


class NoRetryStrategy(RetryStrategy):
    """Для SMS: кожна спроба коштує грошей провайдеру, тому лише одна спроба."""

    def send(self, sender: Sender, order: Order) -> bool:
        try:
            sender(order)
            return True
        except ConnectionError as error:
            print(f"  [no-retry] order {order.id}: failed once, not retrying ({error})")
            return False
