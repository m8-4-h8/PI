"""Composition root: тут і лише тут обираються конкретні реалізації."""

from shop.discounts.standard import StandardDiscount
from shop.discounts.vip import VipDiscount
from shop.extensions.paypal import PayPalPaymentProcessor
from shop.extensions.sms import SmsNotifier
from shop.extensions.wholesale import WholesaleDiscount
from shop.models import Item, Order
from shop.notifiers.email import EmailNotifier
from shop.order_service import OrderService
from shop.payments.credit_card import CreditCardPaymentProcessor
from shop.payments.crypto import CryptoPaymentProcessor
from shop.repositories.mysql import MySqlOrderRepository
from shop.validation import NonEmptyOrderValidator


def build_base_service() -> OrderService:
    """Та сама поведінка, що й у старому OrderProcessor."""
    return OrderService(
        validator=NonEmptyOrderValidator(),
        discounts={"VIP": VipDiscount(), "Standard": StandardDiscount()},
        payments={"CreditCard": CreditCardPaymentProcessor(), "Crypto": CryptoPaymentProcessor()},
        repository=MySqlOrderRepository(),
        notifier=EmailNotifier(),
    )


def build_extended_service() -> OrderService:
    """Завдання 3: Wholesale, PayPal і SMS підключені без зміни жодного наявного класу."""
    return OrderService(
        validator=NonEmptyOrderValidator(),
        discounts={
            "VIP": VipDiscount(),
            "Standard": StandardDiscount(),
            "Wholesale": WholesaleDiscount(),
        },
        payments={
            "CreditCard": CreditCardPaymentProcessor(),
            "Crypto": CryptoPaymentProcessor(),
            "PayPal": PayPalPaymentProcessor(),
        },
        repository=MySqlOrderRepository(),
        notifier=SmsNotifier(),
    )


def main() -> None:
    items = [Item("Laptop", 1000.0), Item("Mouse", 50.0)]

    print("=== Базова конфігурація ===")
    base = build_base_service()
    base.process_order(Order(1, "VIP", "vip@example.com", items=items), "CreditCard")

    print("\n=== Розширена конфігурація (Завдання 3) ===")
    extended = build_extended_service()
    extended.process_order(
        Order(2, "Wholesale", "shop@example.com", "+380501234567", items=items), "PayPal"
    )


if __name__ == "__main__":
    main()
