from notifications.models import Booking
from notifications.observers.base import BookingObserver


class HotelBookingService:
    """Subject: зберігає підписників і сповіщає їх, не знаючи, скільки каналів існує і які саме."""

    def __init__(self) -> None:
        self._observers: list[BookingObserver] = []

    def subscribe(self, observer: BookingObserver) -> None:
        self._observers.append(observer)

    def unsubscribe(self, observer: BookingObserver) -> None:
        self._observers.remove(observer)

    def place_booking(self, booking: Booking) -> None:
        print(f"Saving booking {booking.id}...")
        for observer in self._observers:
            observer.notify(booking)
