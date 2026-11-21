"""Швидка перевірка: python test_notifications.py"""

import ast
from pathlib import Path

from notifications.factory.sender_factory import SenderFactory
from notifications.gateways.base import MessageGateway
from notifications.models import Guest, Booking
from notifications.observers.email_observer import EmailObserver
from notifications.observers.push_observer import PushObserver
from notifications.observers.sms_observer import SmsObserver
from notifications.booking_service import HotelBookingService
from notifications.retry.exponential_backoff import ExponentialBackoffStrategy
from notifications.retry.fixed_delay import FixedDelayStrategy
from notifications.retry.no_retry import NoRetryStrategy


class CountingGateway(MessageGateway):
    def __init__(self, fail_times: int = 0) -> None:
        self.calls = 0
        self.delivered = 0
        self._fail = fail_times

    def send(self, address: str, text: str) -> None:
        self.calls += 1
        if self._fail > 0:
            self._fail -= 1
            raise ConnectionError("down")
        self.delivered += 1


def no_sleep(_):
    pass


ALL = Guest("a@b.c", "+380", frozenset({"email", "sms", "push"}))


def test_backoff_retries_until_success():
    gw = CountingGateway(fail_times=2)
    EmailObserver(gw, ExponentialBackoffStrategy(sleep=no_sleep)).notify(Booking(1, ALL, 1))
    assert (gw.calls, gw.delivered) == (3, 1)


def test_sms_does_not_retry():
    gw = CountingGateway(fail_times=1)
    SmsObserver(gw, NoRetryStrategy()).notify(Booking(1, ALL, 1))
    assert (gw.calls, gw.delivered) == (1, 0)


def test_fixed_delay_waits_same_time():
    waits = []
    gw = CountingGateway(fail_times=2)
    PushObserver(gw, FixedDelayStrategy(delay=0.5, sleep=waits.append)).notify(Booking(1, ALL, 1))
    assert waits == [0.5, 0.5] and gw.delivered == 1


def test_customer_preferences_respected():
    gw = CountingGateway()
    SmsObserver(gw, NoRetryStrategy()).notify(Booking(1, Guest("x@y.z"), 1))
    assert gw.calls == 0


def test_factory_builds_right_pairs():
    f = SenderFactory({"email": CountingGateway(), "sms": CountingGateway(), "push": CountingGateway()})
    pairs = {ch: (type(o).__name__, type(o._retry).__name__) for ch in ("email", "sms", "push") for o in [f.create(ch)]}
    assert pairs == {
        "email": ("EmailObserver", "ExponentialBackoffStrategy"),
        "sms": ("SmsObserver", "NoRetryStrategy"),
        "push": ("PushObserver", "FixedDelayStrategy"),
    }


def test_service_notifies_every_observer():
    service, seen = HotelBookingService(), []

    class Spy:
        def notify(self, booking):
            seen.append(booking.id)

    service.subscribe(Spy())
    service.subscribe(Spy())
    service.place_booking(Booking(7, ALL, 1))
    assert seen == [7, 7]


def test_booking_service_has_no_type_checks():
    source = Path("notifications/booking_service.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "isinstance" not in calls and '"email"' not in source and '"sms"' not in source


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("all tests passed")
