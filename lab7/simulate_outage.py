"""Порівняння: 11-хвилинний збій payment-svc у синхронній і асинхронній версіях.

Хвилини 0..29, щохвилини 3 нові бронювання. payment-svc недоступний у хвилини 10..20 (11 хв).
"""
from simulation.event_log import Topic
from simulation.services import Bank, PaymentService, RoomAssignmentService

MINUTES = 30
BOOKINGS_PER_MINUTE = 3
OUTAGE = range(10, 21)          # 11 хвилин


def booking_amount(n: int) -> float:
    return 2000.0 + 100 * (n % 5)


def run_sync() -> dict:
    """Booking-svc синхронно чекає payment-svc; при збої клієнт отримує 503, бронювання немає."""
    bank, confirmed, failed = Bank(), 0, 0
    for minute in range(MINUTES):
        for i in range(BOOKINGS_PER_MINUTE):
            booking_id = f"bk-{minute:02d}-{i}"
            if minute in OUTAGE:
                failed += 1                       # 503 Service Unavailable
            else:
                bank.charge(booking_id, booking_amount(i))
                confirmed += 1
    return {"created": MINUTES * BOOKINGS_PER_MINUTE, "confirmed": confirmed,
            "rejected_503": failed, "charges": len(bank.charges)}


def run_async(log_lines: list[str]) -> dict:
    bookings, payments, rooms = Topic("bookings"), Topic("payments"), Topic("rooms")
    bank = Bank()
    payment_svc = PaymentService(bookings, payments, bank)
    room_svc = RoomAssignmentService(payments, rooms, free_rooms=1000)
    max_lag = 0

    for minute in range(MINUTES):
        payment_svc.available = minute not in OUTAGE
        for i in range(BOOKINGS_PER_MINUTE):
            booking_id = f"bk-{minute:02d}-{i}"
            bookings.publish("booking.created", booking_id,
                             {"booking_id": booking_id, "amount": booking_amount(i)})
        if minute == OUTAGE.stop:                 # перша хвилина після відновлення
            log_lines.append(f"хв {minute:02d}: payment-svc відновився, lag = {payment_svc.consumer.lag}")
        handled = payment_svc.run_once()
        room_svc.run_once()
        max_lag = max(max_lag, payment_svc.consumer.lag)
        if minute in (OUTAGE.start, OUTAGE.stop - 1, OUTAGE.stop):
            log_lines.append(f"хв {minute:02d}: payment-svc {'UP  ' if payment_svc.available else 'DOWN'}"
                             f" оброблено {handled:>2}, lag після = {payment_svc.consumer.lag}")

    # Повторна доставка: payment-svc впав після списання, але до commit offset.
    bookings.publish("booking.created", "bk-dup", {"booking_id": "bk-dup", "amount": 2500.0})
    payment_svc.crash_before_commit_once = True
    payment_svc.run_once()                        # списав, але offset не закомітив
    payment_svc.run_once()                        # та сама подія прийшла вдруге
    room_svc.run_once()
    dup_charges = sum(1 for key, _ in bank.charges if key == "bk-dup")

    return {"created": len(bookings.events), "captured": len(payments.events),
            "assigned": sum(1 for e in rooms.events if e.type == "room.assigned"),
            "charges": len(bank.charges), "max_lag": max_lag,
            "final_lag": payment_svc.consumer.lag, "bk_dup_charges": dup_charges}


def main() -> None:
    sync = run_sync()
    print("=== Синхронна версія (booking-svc чекає payment-svc) ===")
    print(f"бронювань спробували: {sync['created']}, підтверджено: {sync['confirmed']}, "
          f"відмов 503: {sync['rejected_503']}, списань: {sync['charges']}")

    lines: list[str] = []
    result = run_async(lines)
    print("\n=== Асинхронна версія (Kafka-подібний журнал) ===")
    for line in lines:
        print(line)
    print(f"booking.created: {result['created']}, payment.captured: {result['captured']}, "
          f"room.assigned: {result['assigned']}, списань у банку: {result['charges']}")
    print(f"максимальний lag: {result['max_lag']}, lag у кінці: {result['final_lag']}")
    print(f"подія bk-dup доставлена двічі, списань за нею: {result['bk_dup_charges']}")


if __name__ == "__main__":
    main()
