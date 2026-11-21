from shop.payments.base import PaymentProcessor


class CreditCardPaymentProcessor(PaymentProcessor):
    def pay(self, amount: float) -> None:
        print(f"Processing credit card payment for {amount}")
        # Stripe API call...
