"""EmailObserver з Лабораторної №2, тепер формально реалізує NotificationPort."""
from hotel.application.ports import NotificationPort
from hotel.domain.booking import HotelBooking


class EmailObserver(NotificationPort):
    def __init__(self, send=print) -> None:
        self._send = send  # транспорт; у реальному застосунку — SMTP-клієнт

    def notify(self, booking: HotelBooking) -> None:
        if booking.guest_email:
            self._send(f"Email to {booking.guest_email}: booking {booking.id} confirmed, "
                       f"room {booking.room_number}, {booking.nights} night(s)")
