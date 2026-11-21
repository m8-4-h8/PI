from hotel.models import Booking
from hotel.repositories.base import BookingRepository


class MySqlBookingRepository(BookingRepository):
    def save(self, booking: Booking, total: float) -> None:
        print(f"Saving booking {booking.id} (total {total}) to MySQL Database...")
