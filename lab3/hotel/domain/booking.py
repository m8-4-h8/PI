"""Domain-шар: бронювання номера.

ГАРАНТІЯ: цей файл не має жодних зовнішніх залежностей, за жодних обставин.
Тут лише дані та бізнес-правила. Жодних psycopg2, flask, requests, SQL чи I/O.
Дозволена тільки стандартна бібліотека мови (dataclasses).
"""
from dataclasses import dataclass


class InvalidBookingError(ValueError):
    """Бронювання порушує бізнес-правила."""


@dataclass(frozen=True)
class HotelBooking:
    id: int
    guest_id: int
    room_number: str
    nights: int
    total: float
    guest_email: str = ""
    guest_phone: str = ""

    @property
    def is_valid(self) -> bool:
        """Бізнес-правило: сума бронювання > 0 і хоча б одна ніч."""
        return self.total > 0 and self.nights > 0
