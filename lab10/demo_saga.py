"""Завдання 6. Два сценарії Saga: щасливий шлях і номер зайняли після оплати."""
from resilience.saga import BookingSagaOrchestrator, PaymentService, RoomInventoryService

saga = BookingSagaOrchestrator(PaymentService(), RoomInventoryService({"double": 1}))
for booking_id in ("bk_1", "bk_2"):
    booking = saga.place_booking(booking_id, "double", 4500)
    print(f"=== {booking_id}: {booking.status.value} ===")
    for step in booking.history:
        print(f"  {step}")
print("Сповіщення гостям:")
for note in saga.notifications:
    print(f"  {note}")
