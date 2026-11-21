# Вихідний код (варіант 1): бізнес-логіка переплетена з psycopg2 і SQL.
class HotelBookingService:
    def __init__(self, db_connection):
        self.db = db_connection  # прямий psycopg2-конектор

    def place_booking(self, booking):
        if booking.total <= 0:
            raise ValueError("total must be positive")
        cursor = self.db.cursor()
        cursor.execute(
            "INSERT INTO bookings (id, guest_id, room_number, nights, total) VALUES (%s, %s, %s, %s, %s)",
            (booking.id, booking.guest_id, booking.room_number, booking.nights, booking.total),
        )
        self.db.commit()
        # ... виклики EmailObserver/SmsObserver з Лабораторної №2 ...
