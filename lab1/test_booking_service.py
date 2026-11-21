"""Швидка перевірка: python -m pytest -q (або python test_booking_service.py)."""

import ast
from pathlib import Path

from main import build_base_service, build_extended_service
from hotel.booking_service import UnsupportedOptionError
from hotel.models import Booking, Room
from hotel.validation import BookingValidationError

ROOMS = [Room("101", 100.0), Room("102", 100.0)]


def test_discounts():
    assert build_base_service().process_booking(Booking(1, "VIP", "a@b.c", rooms=ROOMS), "CreditCard") == 160.0
    assert build_base_service().process_booking(Booking(2, "Standard", "a@b.c", rooms=ROOMS), "Crypto") == 190.0
    assert build_extended_service().process_booking(Booking(3, "Corporate", "a@b.c", rooms=ROOMS), "PayPal") == 140.0


def test_booking_without_rooms_rejected():
    try:
        build_base_service().process_booking(Booking(4, "VIP", "a@b.c"), "CreditCard")
    except BookingValidationError:
        return
    raise AssertionError("booking without rooms must be rejected")


def test_unknown_payment_rejected_before_saving():
    try:
        build_base_service().process_booking(Booking(5, "VIP", "a@b.c", rooms=ROOMS), "Cash")
    except UnsupportedOptionError:
        return
    raise AssertionError("unknown payment type must be rejected")


def test_unknown_guest_type_rejected():
    try:
        build_base_service().process_booking(Booking(6, "Corporate", "a@b.c", rooms=ROOMS), "CreditCard")
    except UnsupportedOptionError:
        return
    raise AssertionError("Corporate is not configured in the base service")


def test_booking_service_depends_only_on_abstractions():
    path = Path(__file__).parent / "hotel" / "booking_service.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    concrete = {m for m in imported if m.split(".")[-1] not in {"base", "models", "validation", "abc"}}
    concrete.discard("collections.abc")
    assert not concrete, f"HotelBookingService imports concrete modules: {concrete}"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("all tests passed")
