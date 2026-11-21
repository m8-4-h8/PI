from dataclasses import dataclass, field


@dataclass(frozen=True)
class Room:
    number: str
    price: float  # вартість номера за весь період проживання


@dataclass
class Booking:
    id: int
    guest_type: str
    guest_email: str
    guest_phone: str = ""
    rooms: list[Room] = field(default_factory=list)

    @property
    def subtotal(self) -> float:
        return sum(room.price for room in self.rooms)
