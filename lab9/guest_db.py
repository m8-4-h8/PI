"""Тестова база гостей (SQLite у пам'яті) для демонстрації ін'єкції."""
import sqlite3

GUESTS = [
    (1, "Shevchenko", "taras@example.com", "+380501111111", 1200),
    (2, "Kovalenko", "olena@example.com", "+380502222222", 300),
    (3, "Bondarenko", "ivan@example.com", "+380503333333", 50),
    (4, "O'Brien", "sean@example.com", "+353861234567", 900),
    (5, "Kovalenko", "petro@example.com", "+380505555555", 0),
]


def make_db() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:", check_same_thread=False)
    db.execute("CREATE TABLE guests (id INTEGER PRIMARY KEY, last_name TEXT, email TEXT, "
               "phone TEXT, loyalty_points INTEGER)")
    db.executemany("INSERT INTO guests VALUES (?, ?, ?, ?, ?)", GUESTS)
    db.commit()
    return db
