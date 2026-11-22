"""Сервіси варіанта 1: booking -> payment -> room-assignment."""
from simulation.event_log import ConsumerGroup, Event, Topic


class Bank:
    """Зовнішній процесинговий банк. Ідемпотентний за ключем (як Idempotency-Key у Stripe)."""

    def __init__(self) -> None:
        self.charges: list[tuple[str, float]] = []
        self._by_key: dict[str, str] = {}

    def charge(self, idempotency_key: str, amount: float) -> str:
        if idempotency_key in self._by_key:
            return self._by_key[idempotency_key]
        charge_id = f"ch_{len(self.charges) + 1}"
        self.charges.append((idempotency_key, amount))
        self._by_key[idempotency_key] = charge_id
        return charge_id


class PaymentService:
    """Споживач booking.created. Захист від подвійного списання -- таблиця processed_payments
    з унікальним ключем booking_id (у реальній системі -- UNIQUE у PostgreSQL)."""

    def __init__(self, bookings: Topic, payments: Topic, bank: Bank) -> None:
        self.consumer = ConsumerGroup(bookings, "payment-svc")
        self.payments = payments
        self.bank = bank
        self.available = True
        self.processed_payments: dict[str, str] = {}   # booking_id -> charge_id
        self.crash_before_commit_once = False

    def run_once(self) -> int:
        if not self.available:
            return 0
        handled = 0
        for event in self.consumer.poll():
            self.handle(event)
            if self.crash_before_commit_once:          # падіння між обробкою і commit
                self.crash_before_commit_once = False
                return handled
            self.consumer.commit(event)
            handled += 1
        return handled

    def handle(self, event: Event) -> None:
        booking_id = event.payload["booking_id"]
        if booking_id in self.processed_payments:      # дубль -- банк не викликаємо
            return
        if event.payload["amount"] <= 0:
            self.payments.publish("payment.failed", booking_id,
                                  {"booking_id": booking_id, "reason": "invalid_amount"})
            self.processed_payments[booking_id] = "failed"
            return
        charge_id = self.bank.charge(idempotency_key=booking_id, amount=event.payload["amount"])
        self.processed_payments[booking_id] = charge_id
        self.payments.publish("payment.captured", booking_id,
                              {"booking_id": booking_id, "charge_id": charge_id,
                               "amount": event.payload["amount"]})


class RoomAssignmentService:
    """Споживач payment.captured: призначає конкретний номер або публікує room.unavailable."""

    def __init__(self, payments: Topic, rooms: Topic, free_rooms: int) -> None:
        self.consumer = ConsumerGroup(payments, "room-assignment-svc")
        self.rooms = rooms
        self.free_rooms = free_rooms
        self.assigned: dict[str, str] = {}

    def run_once(self) -> None:
        for event in self.consumer.poll():
            if event.type == "payment.captured" and event.key not in self.assigned:
                if self.free_rooms > 0:
                    self.free_rooms -= 1
                    self.assigned[event.key] = f"room-{100 + len(self.assigned)}"
                    self.rooms.publish("room.assigned", event.key,
                                       {"booking_id": event.key, "room": self.assigned[event.key]})
                else:
                    self.assigned[event.key] = "none"
                    self.rooms.publish("room.unavailable", event.key, {"booking_id": event.key})
            self.consumer.commit(event)
