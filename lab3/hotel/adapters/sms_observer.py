"""SmsObserver з Лабораторної №2, тепер формально реалізує NotificationPort."""
from hotel.application.ports import NotificationPort
from hotel.domain.booking import HotelBooking


class SmsObserver(NotificationPort):
    def __init__(self, send=print) -> None:
        self._send = send  # транспорт; у реальному застосунку — SMS-шлюз

    def notify(self, booking: HotelBooking) -> None:
        if booking.guest_phone:
            self._send(f"SMS to {booking.guest_phone}: booking {booking.id} confirmed")
