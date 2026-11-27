"""Демонстрація LoyaltyDiscountCalculator (лаба 4, варіант 1).

Запуск з будь-якої папки:  python lab4/main.py   або   python main.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loyalty.discount import LoyaltyDiscountCalculator  # noqa: E402


def main() -> None:
    calc = LoyaltyDiscountCalculator()
    print("Знижка лояльності: 10% від суми бронювання 1000 грн включно")
    for total in (500, 999.99, 1000, 2000):
        print(f"  бронювання {total:>8} грн -> знижка {calc.calculate(total):.2f} грн")


if __name__ == "__main__":
    main()
