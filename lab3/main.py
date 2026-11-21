"""Composition root: тільки тут обираються конкретні адаптери.

python main.py                  — демо з InMemoryOrderRepository (база не потрібна)
BOOKING_DSN=... python main.py  — та сама збірка з SqlHotelBookingRepository (PostgreSQL)
"""
import os

from hotel.adapters.email_observer import EmailObserver
from hotel.adapters.in_memory_repository import InMemoryOrderRepository
from hotel.adapters.sms_observer import SmsObserver
from hotel.adapters.sql_repository import SqlHotelBookingRepository
from hotel.application.place_booking import PlaceBookingUseCase
from hotel.domain.booking import HotelBooking, InvalidBookingError


def build_use_case(repo) -> PlaceBookingUseCase:
    return PlaceBookingUseCase(repo=repo, notifiers=[EmailObserver(), SmsObserver()])


def main() -> None:
    dsn = os.environ.get("BOOKING_DSN")
    if dsn:
        repo = SqlHotelBookingRepository.from_dsn(dsn)
        print("Репозиторій: SqlHotelBookingRepository (PostgreSQL)")
    else:
        repo = InMemoryOrderRepository()
        print("Репозиторій: InMemoryOrderRepository (BOOKING_DSN не задано)")

    use_case = build_use_case(repo)
    use_case.execute(HotelBooking(id=101, guest_id=7, room_number="305", nights=3, total=4500.0,
                                  guest_email="guest@example.com", guest_phone="+380501234567"))
    try:
        use_case.execute(HotelBooking(id=102, guest_id=8, room_number="12", nights=2, total=0))
    except InvalidBookingError as error:
        print(f"Відхилено: {error}")


if __name__ == "__main__":
    main()
