"""Завдання 6. Saga бронювання з оркестратором BookingService (in-memory модель).

Кожен сервіс має власну «базу» і робить локальний ACID COMMIT своєї зміни.
Компенсація -- окрема бізнес-операція (Refund), а не відкат транзакції.
"""
from dataclasses import dataclass, field
from enum import Enum


class BookingStatus(Enum):
    PENDING = "PENDING"
    PAYMENT_CAPTURED = "PAYMENT_CAPTURED"
    CONFIRMED = "CONFIRMED"
    COMPENSATING = "COMPENSATING"
    CANCELLED = "CANCELLED"


class RoomUnavailable(Exception):
    pass


@dataclass
class PaymentService:
    payments: dict = field(default_factory=dict)        # booking_id -> запис оплати
    refunds: dict = field(default_factory=dict)

    def charge(self, booking_id: str, amount: int) -> str:     # команда ChargePayment
        if booking_id in self.payments:                         # ідемпотентно за booking_id
            return self.payments[booking_id]["charge_id"]
        charge_id = f"ch_{len(self.payments) + 1}"
        self.payments[booking_id] = {"charge_id": charge_id, "amount": amount}   # COMMIT
        return charge_id

    def refund(self, booking_id: str) -> str:                   # компенсація RefundPayment
        if booking_id in self.refunds:                          # ідемпотентно
            return self.refunds[booking_id]["refund_id"]
        payment = self.payments[booking_id]
        refund_id = f"re_{len(self.refunds) + 1}"
        self.refunds[booking_id] = {"refund_id": refund_id, "charge_id": payment["charge_id"],
                                    "amount": payment["amount"]}                  # COMMIT
        return refund_id


@dataclass
class RoomInventoryService:
    free_rooms: dict                                            # room_type -> кількість
    reservations: dict = field(default_factory=dict)

    def reserve(self, booking_id: str, room_type: str) -> str:  # команда ReserveRoom
        if booking_id in self.reservations:
            return self.reservations[booking_id]
        if self.free_rooms.get(room_type, 0) <= 0:
            raise RoomUnavailable(room_type)                    # локальна транзакція відкотилась
        self.free_rooms[room_type] -= 1
        self.reservations[booking_id] = f"{room_type}-{len(self.reservations) + 1}"   # COMMIT
        return self.reservations[booking_id]


@dataclass
class Booking:
    id: str
    room_type: str
    amount: int
    status: BookingStatus = BookingStatus.PENDING
    history: list = field(default_factory=list)


class BookingSagaOrchestrator:
    """BookingService у ролі оркестратора: знає всі кроки і глобальний статус бронювання."""

    def __init__(self, payment: PaymentService, inventory: RoomInventoryService) -> None:
        self.payment = payment
        self.inventory = inventory
        self.bookings: dict[str, Booking] = {}
        self.notifications: list[str] = []

    def _set(self, booking: Booking, status: BookingStatus, note: str) -> None:
        booking.status = status                                  # COMMIT у bookings DB
        booking.history.append(f"{status.value}: {note}")

    def place_booking(self, booking_id: str, room_type: str, amount: int) -> Booking:
        booking = Booking(booking_id, room_type, amount)
        self.bookings[booking_id] = booking
        booking.history.append("PENDING: booking created (BookingService COMMIT)")

        charge_id = self.payment.charge(booking_id, amount)
        self._set(booking, BookingStatus.PAYMENT_CAPTURED, f"PaymentCaptured {charge_id} (PaymentService COMMIT)")
        try:
            room = self.inventory.reserve(booking_id, room_type)
        except RoomUnavailable:
            self._set(booking, BookingStatus.COMPENSATING, "RoomUnavailable (RoomInventoryService нічого не змінив)")
            refund_id = self.payment.refund(booking_id)
            self._set(booking, BookingStatus.CANCELLED, f"PaymentRefunded {refund_id} (PaymentService COMMIT)")
            self.notifications.append(f"{booking_id}: на жаль, номер {room_type} уже зайнятий, кошти повернено ({refund_id})")
            return booking
        self._set(booking, BookingStatus.CONFIRMED, f"RoomReserved {room} (RoomInventoryService COMMIT)")
        self.notifications.append(f"{booking_id}: бронювання підтверджено, номер {room}")
        return booking
