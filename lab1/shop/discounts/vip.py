from shop.discounts.base import DiscountStrategy


class VipDiscount(DiscountStrategy):
    def rate(self) -> float:
        return 0.20
