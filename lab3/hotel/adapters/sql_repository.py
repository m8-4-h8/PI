"""Адаптер PostgreSQL. ЄДИНЕ місце в системі, де є SQL і psycopg2."""
try:
    import psycopg2
except ImportError:  # psycopg2 потрібен лише для роботи з реальною базою
    psycopg2 = None

from hotel.application.ports import OrderRepositoryPort
from hotel.domain.booking import HotelBooking

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS bookings (
    id          INTEGER PRIMARY KEY,
    guest_id    INTEGER NOT NULL,
    room_number TEXT    NOT NULL,
    nights      INTEGER NOT NULL,
    total       NUMERIC(10, 2) NOT NULL
)
"""

INSERT_SQL = (
    "INSERT INTO bookings (id, guest_id, room_number, nights, total) "
    "VALUES (%s, %s, %s, %s, %s)"
)


class SqlHotelBookingRepository(OrderRepositoryPort):
    def __init__(self, connection) -> None:
        self._db = connection

    @classmethod
    def from_dsn(cls, dsn: str) -> "SqlHotelBookingRepository":
        if psycopg2 is None:
            raise RuntimeError("pip install psycopg2-binary, щоб працювати з PostgreSQL")
        repo = cls(psycopg2.connect(dsn))
        repo.create_schema()
        return repo

    def create_schema(self) -> None:
        with self._db.cursor() as cursor:
            cursor.execute(CREATE_TABLE_SQL)
        self._db.commit()

    def save(self, booking: HotelBooking) -> None:
        with self._db.cursor() as cursor:
            cursor.execute(
                INSERT_SQL,
                (booking.id, booking.guest_id, booking.room_number, booking.nights, booking.total),
            )
        self._db.commit()
