"""Потрібен PostgreSQL (BOOKING_DSN). Без нього тест пропускається."""
import os

import pytest

psycopg2 = pytest.importorskip("psycopg2")
import double_booking_demo as demo  # noqa: E402


def db_available():
    try:
        psycopg2.connect(demo.DSN).close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not db_available(), reason="PostgreSQL недоступний")
def test_conditional_update_gives_exactly_one_winner_and_one_ticket():
    naive, safe, tickets = demo.main()
    assert safe == 1 and tickets == 1
    assert naive >= 1
