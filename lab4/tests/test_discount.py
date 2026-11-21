from loyalty.discount import LoyaltyDiscountCalculator


# --- існуючі тести попереднього розробника (не змінювались) ---

def test_no_discount_below_threshold():
    calc = LoyaltyDiscountCalculator()
    assert calc.calculate(500) == 0


def test_discount_above_threshold():
    calc = LoyaltyDiscountCalculator()
    assert calc.calculate(2000) == 200


# --- Завдання 1. RED: повна специфікація «від 1000 грн включно» ---

def test_discount_at_threshold_is_applied():
    calc = LoyaltyDiscountCalculator()
    assert calc.calculate(1000) == 100


# --- Завдання 3. Property-based тести ---

from hypothesis import example, given, settings, strategies as st

totals = st.floats(min_value=0, max_value=100_000, allow_nan=False, allow_infinity=False)


# Випадкові float майже ніколи не влучають рівно в 1000, тому межові точки
# додано явно через @example — генератор при цьому працює як завжди.
@settings(max_examples=500)
@given(total=totals)
@example(total=1000.0)
@example(total=999.99)
def test_property_discount_matches_specification(total):
    """Інваріант (б) для варіанта 1: для будь-якої суми від 0 до 100 000 (і дробової)
    знижка дорівнює рівно 10% від суми, якщо total >= 1000, і рівно 0.0, якщо total < 1000.
    """
    discount = LoyaltyDiscountCalculator().calculate(total)
    if total >= 1000:
        assert discount == total * 0.10
    else:
        assert discount == 0.0


@given(total=totals)
def test_property_discount_is_never_negative_and_never_above_ten_percent(total):
    """Інваріант (а): знижка ніколи не від'ємна і ніколи не перевищує 10% суми."""
    discount = LoyaltyDiscountCalculator().calculate(total)
    assert 0.0 <= discount <= total * 0.10
