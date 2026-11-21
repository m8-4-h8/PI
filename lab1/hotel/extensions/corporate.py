from hotel.discounts.base import DiscountStrategy


class CorporateDiscount(DiscountStrategy):
    """Завдання 3: новий тип гостя «Corporate» (корпоративний клієнт), знижка 30%."""

    def rate(self) -> float:
        return 0.30
