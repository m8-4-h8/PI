from shop.discounts.base import DiscountStrategy


class StandardDiscount(DiscountStrategy):
    def rate(self) -> float:
        return 0.05
