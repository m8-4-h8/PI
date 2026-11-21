from dataclasses import dataclass, field


@dataclass(frozen=True)
class Item:
    name: str
    price: float


@dataclass
class Order:
    id: int
    customer_type: str
    customer_email: str
    customer_phone: str = ""
    items: list[Item] = field(default_factory=list)

    @property
    def subtotal(self) -> float:
        return sum(item.price for item in self.items)
