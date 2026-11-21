from hotel.payments.base import PaymentProcessor


class PayPalPaymentProcessor(PaymentProcessor):
    """Завдання 3: новий спосіб оплати PayPal."""

    def pay(self, amount: float) -> None:
        print(f"Processing PayPal payment for {amount}")
        # PayPal API call...
