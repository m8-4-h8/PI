"""Use case «Забронювати номер». Працює ЛИШЕ через порти."""
from hotel.application.ports import NotificationPort, OrderRepositoryPort
from hotel.domain.booking import HotelBooking, InvalidBookingError


class PlaceBookingUseCase:
    def __init__(self, repo: OrderRepositoryPort, notifiers: list[NotificationPort]) -> None:
        self._repo = repo
        self._notifiers = list(notifiers)

    def execute(self, booking: HotelBooking) -> HotelBooking:
        if not booking.is_valid:
            raise InvalidBookingError(
                f"booking {booking.id}: total must be > 0 and nights > 0"
            )
        self._repo.save(booking)
        for notifier in self._notifiers:
            notifier.notify(booking)
        return booking
