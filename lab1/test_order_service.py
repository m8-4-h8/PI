"""Швидка перевірка: python -m pytest -q (або python test_order_service.py)."""

import ast
from pathlib import Path

from main import build_base_service, build_extended_service
from shop.models import Item, Order
from shop.order_service import UnsupportedOptionError
from shop.validation import OrderValidationError

ITEMS = [Item("A", 100.0), Item("B", 100.0)]


def test_discounts():
    assert build_base_service().process_order(Order(1, "VIP", "a@b.c", items=ITEMS), "CreditCard") == 160.0
    assert build_base_service().process_order(Order(2, "Standard", "a@b.c", items=ITEMS), "Crypto") == 190.0
    assert build_extended_service().process_order(Order(3, "Wholesale", "a@b.c", items=ITEMS), "PayPal") == 140.0


def test_empty_order_rejected():
    try:
        build_base_service().process_order(Order(4, "VIP", "a@b.c"), "CreditCard")
    except OrderValidationError:
        return
    raise AssertionError("empty order must be rejected")


def test_unknown_payment_rejected_before_saving():
    try:
        build_base_service().process_order(Order(5, "VIP", "a@b.c", items=ITEMS), "Cash")
    except UnsupportedOptionError:
        return
    raise AssertionError("unknown payment type must be rejected")


def test_order_service_depends_only_on_abstractions():
    tree = ast.parse(Path("shop/order_service.py").read_text(encoding="utf-8"))
    imported = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    concrete = {m for m in imported if m.split(".")[-1] not in {"base", "models", "validation", "abc"}}
    concrete.discard("collections.abc")
    assert not concrete, f"OrderService imports concrete modules: {concrete}"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("all tests passed")
