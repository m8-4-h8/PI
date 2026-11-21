"""Тести use case без PostgreSQL. Запуск: python test_place_booking.py (або pytest)."""
import ast
import os
from pathlib import Path

from hotel.adapters.in_memory_repository import InMemoryOrderRepository
from hotel.application.ports import NotificationPort
from hotel.application.place_booking import PlaceBookingUseCase
from hotel.domain.booking import HotelBooking, InvalidBookingError

ROOT = Path(__file__).parent


class FakeNotifier(NotificationPort):
    def __init__(self) -> None:
        self.notified: list[HotelBooking] = []

    def notify(self, booking: HotelBooking) -> None:
        self.notified.append(booking)


def make_booking(**overrides) -> HotelBooking:
    data = dict(id=1, guest_id=10, room_number="305", nights=2, total=3000.0)
    data.update(overrides)
    return HotelBooking(**data)


def test_valid_booking_is_saved_and_notified():
    repo, notifier = InMemoryOrderRepository(), FakeNotifier()
    booking = make_booking()

    result = PlaceBookingUseCase(repo, [notifier]).execute(booking)

    assert result == booking
    assert repo.bookings == [booking]
    assert notifier.notified == [booking]


def test_every_notifier_is_called():
    repo, first, second = InMemoryOrderRepository(), FakeNotifier(), FakeNotifier()
    booking = make_booking()

    PlaceBookingUseCase(repo, [first, second]).execute(booking)

    assert first.notified == [booking] and second.notified == [booking]


def test_invalid_booking_is_not_saved_and_not_notified():
    for bad in (make_booking(total=0), make_booking(total=-100), make_booking(nights=0)):
        repo, notifier = InMemoryOrderRepository(), FakeNotifier()
        try:
            PlaceBookingUseCase(repo, [notifier]).execute(bad)
        except InvalidBookingError:
            pass
        else:
            raise AssertionError(f"{bad} should be rejected")
        assert repo.bookings == [] and notifier.notified == []


FORBIDDEN = {"psycopg2", "flask", "requests", "sqlalchemy", "sqlite3", "hotel.adapters"}


def imported_modules(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_dependency_rule_domain_and_application_have_no_framework_imports():
    files = list((ROOT / "hotel" / "domain").glob("*.py")) + list((ROOT / "hotel" / "application").glob("*.py"))
    for path in files:
        for module in imported_modules(path):
            assert not any(module == f or module.startswith(f + ".") for f in FORBIDDEN), \
                f"{path.relative_to(ROOT)} imports {module}"


def test_domain_imports_nothing_from_outer_layers():
    for path in (ROOT / "hotel" / "domain").glob("*.py"):
        for module in imported_modules(path):
            assert not module.startswith("hotel.application"), f"{path.name} imports {module}"


def test_sql_adapter_with_real_postgres_if_available():
    """Інтеграційний тест. Пропускається, якщо BOOKING_DSN не задано."""
    dsn = os.environ.get("BOOKING_DSN")
    if not dsn:
        print("  (skip) BOOKING_DSN не задано — інтеграційний тест з PostgreSQL пропущено")
        return
    from hotel.adapters.sql_repository import SqlHotelBookingRepository

    repo = SqlHotelBookingRepository.from_dsn(dsn)
    with repo._db.cursor() as cursor:
        cursor.execute("DELETE FROM bookings WHERE id = 999")
    PlaceBookingUseCase(repo, [FakeNotifier()]).execute(make_booking(id=999))
    with repo._db.cursor() as cursor:
        cursor.execute("SELECT room_number, nights, total FROM bookings WHERE id = 999")
        assert cursor.fetchone() == ("305", 2, 3000)
        cursor.execute("DELETE FROM bookings WHERE id = 999")
    repo._db.commit()


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for name, test in tests:
        test()
        print(f"ok  {name}")
    print(f"all {len(tests)} tests passed")
