from resilience.saga import (BookingSagaOrchestrator, BookingStatus, PaymentService,
                             RoomInventoryService)


def test_happy_path_confirms_booking():
    saga = BookingSagaOrchestrator(PaymentService(), RoomInventoryService({"double": 1}))
    booking = saga.place_booking("bk_1", "double", 4500)
    assert booking.status is BookingStatus.CONFIRMED
    assert saga.payment.payments["bk_1"]["amount"] == 4500 and saga.payment.refunds == {}
    assert saga.inventory.reservations == {"bk_1": "double-1"}


def test_room_taken_after_payment_triggers_refund():
    payment, inventory = PaymentService(), RoomInventoryService({"double": 1})
    saga = BookingSagaOrchestrator(payment, inventory)
    saga.place_booking("bk_1", "double", 4500)            # останній номер забрав інший гість
    booking = saga.place_booking("bk_2", "double", 4500)

    assert booking.status is BookingStatus.CANCELLED
    assert [h.split(":")[0] for h in booking.history] == [
        "PENDING", "PAYMENT_CAPTURED", "COMPENSATING", "CANCELLED"]
    assert payment.refunds["bk_2"]["charge_id"] == payment.payments["bk_2"]["charge_id"]
    assert payment.refunds["bk_2"]["amount"] == 4500
    assert "bk_2" in payment.payments                      # списання не «відкочене», а компенсоване
    assert "кошти повернено" in saga.notifications[-1]


def test_refund_is_idempotent():
    payment = PaymentService()
    payment.charge("bk_9", 100)
    assert payment.refund("bk_9") == payment.refund("bk_9") and len(payment.refunds) == 1
