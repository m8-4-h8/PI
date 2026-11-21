"""Composition root: тут і лише тут обираються конкретні реалізації."""

from hotel.booking_service import HotelBookingService
from hotel.discounts.standard import StandardDiscount
from hotel.discounts.vip import VipDiscount
from hotel.extensions.corporate import CorporateDiscount
from hotel.extensions.paypal import PayPalPaymentProcessor
from hotel.extensions.sms import SmsNotifier
from hotel.models import Booking, Room
from hotel.notifiers.email import EmailNotifier
from hotel.payments.credit_card import CreditCardPaymentProcessor
from hotel.payments.crypto import CryptoPaymentProcessor
from hotel.repositories.mysql import MySqlBookingRepository
from hotel.validation import HasRoomsValidator


def build_base_service() -> HotelBookingService:
    """Та сама поведінка, що й у старому HotelBookingProcessor."""
    return HotelBookingService(
        validator=HasRoomsValidator(),
        discounts={"VIP": VipDiscount(), "Standard": StandardDiscount()},
        payments={"CreditCard": CreditCardPaymentProcessor(), "Crypto": CryptoPaymentProcessor()},
        repository=MySqlBookingRepository(),
        notifier=EmailNotifier(),
    )


def build_extended_service() -> HotelBookingService:
    """Завдання 3: Corporate, PayPal і SMS підключені без зміни жодного наявного класу."""
    return HotelBookingService(
        validator=HasRoomsValidator(),
        discounts={
            "VIP": VipDiscount(),
            "Standard": StandardDiscount(),
            "Corporate": CorporateDiscount(),
        },
        payments={
            "CreditCard": CreditCardPaymentProcessor(),
            "Crypto": CryptoPaymentProcessor(),
            "PayPal": PayPalPaymentProcessor(),
        },
        repository=MySqlBookingRepository(),
        notifier=SmsNotifier(),
    )


def main() -> None:
    rooms = [Room("305", 1000.0), Room("306", 50.0)]

    print("=== Базова конфігурація ===")
    base = build_base_service()
    base.process_booking(Booking(1, "VIP", "vip@example.com", rooms=rooms), "CreditCard")

    print("\n=== Розширена конфігурація (Завдання 3) ===")
    extended = build_extended_service()
    extended.process_booking(
        Booking(2, "Corporate", "corp@example.com", "+380501234567", rooms=rooms), "PayPal"
    )


if __name__ == "__main__":
    main()
