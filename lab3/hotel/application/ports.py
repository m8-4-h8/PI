"""Порти шару Application. Лише контракти, без реалізації.

Імпортує тільки Domain і стандартну бібліотеку — нічого з Frameworks.
"""
from abc import ABC, abstractmethod

from hotel.domain.booking import HotelBooking


class OrderRepositoryPort(ABC):
    """Куди зберегти бронювання. Як саме — вирішує адаптер."""

    @abstractmethod
    def save(self, booking: HotelBooking) -> None:
        ...


class NotificationPort(ABC):
    """Як повідомити про бронювання. Канал — вирішує адаптер."""

    @abstractmethod
    def notify(self, booking: HotelBooking) -> None:
        ...
