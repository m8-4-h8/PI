"""Адаптер для тестів: зберігає бронювання у списку в пам'яті."""
from hotel.application.ports import OrderRepositoryPort
from hotel.domain.booking import HotelBooking


class InMemoryOrderRepository(OrderRepositoryPort):
    def __init__(self) -> None:
        self.bookings: list[HotelBooking] = []

    def save(self, booking: HotelBooking) -> None:
        self.bookings.append(booking)
