from abc import ABC, abstractmethod


class DiscountStrategy(ABC):
    """Стратегія знижки для одного типу клієнта."""

    @abstractmethod
    def rate(self) -> float:
        """Частка знижки від 0 до 1."""

    def apply(self, amount: float) -> float:
        return round(amount * (1 - self.rate()), 2)
