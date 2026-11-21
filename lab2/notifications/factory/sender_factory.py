from collections.abc import Callable, Mapping

from notifications.gateways.base import MessageGateway
from notifications.observers.base import OrderObserver
from notifications.observers.email_observer import EmailObserver
from notifications.observers.push_observer import PushObserver
from notifications.observers.sms_observer import SmsObserver
from notifications.retry.exponential_backoff import ExponentialBackoffStrategy
from notifications.retry.fixed_delay import FixedDelayStrategy
from notifications.retry.no_retry import NoRetryStrategy


class SenderFactory:
    """Завдання 4, Factory Method: за ідентифікатором каналу повертає готовий Observer
    з правильною для нього стратегією повторів. Клієнтський код нічого не збирає вручну."""

    def __init__(self, gateways: Mapping[str, MessageGateway], delay_scale: float = 1.0) -> None:
        self._gateways = gateways
        self._scale = delay_scale  # у демо зменшуємо паузи, щоб не чекати секунди
        self._creators: dict[str, Callable[[], OrderObserver]] = {
            "email": self._create_email,
            "sms": self._create_sms,
            "push": self._create_push,
        }

    def create(self, channel: str) -> OrderObserver:
        try:
            creator = self._creators[channel]
        except KeyError:
            raise ValueError(f"Unknown channel: {channel!r}") from None
        return creator()

    def _create_email(self) -> OrderObserver:
        return EmailObserver(self._gateways["email"], ExponentialBackoffStrategy(base_delay=1.0 * self._scale))

    def _create_sms(self) -> OrderObserver:
        return SmsObserver(self._gateways["sms"], NoRetryStrategy())

    def _create_push(self) -> OrderObserver:
        return PushObserver(self._gateways["push"], FixedDelayStrategy(delay=1.0 * self._scale))
