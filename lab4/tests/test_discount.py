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
