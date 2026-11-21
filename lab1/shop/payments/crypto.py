from shop.payments.base import PaymentProcessor


class CryptoPaymentProcessor(PaymentProcessor):
    def pay(self, amount: float) -> None:
        print(f"Processing crypto payment for {amount}")
        # Coinbase API call...
