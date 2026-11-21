"""Знижка лояльності мережі готелів: 10% від суми бронювання 1000 грн включно."""
class LoyaltyDiscountCalculator:
    DISCOUNT_THRESHOLD = 1000
    DISCOUNT_RATE = 0.10

    def calculate(self, booking_total: float) -> float:
        """Повертає суму знижки для бронювання на суму booking_total."""
        if booking_total > self.DISCOUNT_THRESHOLD:
            return booking_total * self.DISCOUNT_RATE
        return 0.0
