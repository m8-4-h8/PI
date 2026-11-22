"""Тести моделі. Запуск: python test_simulation.py (або pytest)."""
from simulate_outage import BOOKINGS_PER_MINUTE, MINUTES, OUTAGE, run_async, run_sync
from simulation.event_log import Topic
from simulation.services import Bank, PaymentService


def test_sync_version_loses_bookings_during_outage():
    result = run_sync()
    assert result["rejected_503"] == len(OUTAGE) * BOOKINGS_PER_MINUTE == 33


def test_async_version_loses_nothing_and_catches_up():
    result = run_async([])
    total = MINUTES * BOOKINGS_PER_MINUTE + 1           # + подія bk-dup
    assert result["created"] == result["captured"] == result["assigned"] == result["charges"] == total
    assert result["max_lag"] == 33 and result["final_lag"] == 0


def test_duplicate_delivery_does_not_double_charge():
    bookings, payments, bank = Topic("b"), Topic("p"), Bank()
    svc = PaymentService(bookings, payments, bank)
    bookings.publish("booking.created", "bk-1", {"booking_id": "bk-1", "amount": 3000.0})
    svc.crash_before_commit_once = True
    svc.run_once()
    assert svc.consumer.lag == 1                         # offset не закомічено -> повторна доставка
    svc.run_once()
    assert len(bank.charges) == 1 and svc.consumer.lag == 0
    assert len(payments.events) == 1                     # payment.captured опубліковано один раз


def test_invalid_amount_produces_payment_failed():
    bookings, payments, bank = Topic("b"), Topic("p"), Bank()
    svc = PaymentService(bookings, payments, bank)
    bookings.publish("booking.created", "bk-0", {"booking_id": "bk-0", "amount": 0})
    svc.run_once()
    assert [e.type for e in payments.events] == ["payment.failed"] and bank.charges == []


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    for name, fn in tests:
        fn()
        print(f"ok  {name}")
    print(f"all {len(tests)} tests passed")
