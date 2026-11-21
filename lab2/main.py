"""Налаштування застосунку: підписка відбувається тут один раз, а не всередині place_order."""

from notifications.factory.sender_factory import SenderFactory
from notifications.gateways.console import ConsoleGateway
from notifications.gateways.flaky import FlakyGateway
from notifications.models import Customer, Order
from notifications.observers.analytics_observer import AnalyticsObserver
from notifications.order_service import OrderService


def main() -> None:
    gateways = {
        # Імітація збоїв мережі, щоб побачити різну поведінку стратегій:
        "email": FlakyGateway(ConsoleGateway("EMAIL"), fail_times=2),  # 2 збої → backoff дочекається
        "sms": FlakyGateway(ConsoleGateway("SMS"), fail_times=1),      # 1 збій → без повтору
        "push": FlakyGateway(ConsoleGateway("PUSH"), fail_times=1),    # 1 збій → фіксована пауза
    }
    factory = SenderFactory(gateways, delay_scale=0.1)

    service = OrderService()
    for channel in ("email", "sms", "push"):
        service.subscribe(factory.create(channel))
    analytics = AnalyticsObserver()
    service.subscribe(analytics)

    alice = Customer("alice@example.com", "+380501112233", frozenset({"email", "sms", "push"}))
    bob = Customer("bob@example.com", channels=frozenset({"email"}))

    print("=== Замовлення 1: email + sms + push ===")
    service.place_order(Order(1, alice, 1050.0))
    print("\n=== Замовлення 2: лише email ===")
    service.place_order(Order(2, bob, 99.9))

    print(f"\nЗаписів у журналі аналітики: {len(analytics.journal)}")


if __name__ == "__main__":
    main()
