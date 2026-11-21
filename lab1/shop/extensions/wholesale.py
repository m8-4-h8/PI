from shop.discounts.base import DiscountStrategy


class WholesaleDiscount(DiscountStrategy):
    """Завдання 3: новий тип клієнта «Wholesale» (оптовик), знижка 30%."""

    def rate(self) -> float:
        return 0.30
