# room_availability_service.py -- НАДАНО (варіант 1), не змінювати цей файл
import time


class SlowRoomAvailabilityService:
    """Емулює похід у реляційну базу даних: кожен виклик -- 150 мс затримки."""

    def __init__(self):
        self._db = {
            f"room-{i}": {"id": f"room-{i}", "hotel_id": f"hotel-{(i - 1) // 10 + 1}",
                          "price_per_night": 1000 + 10 * i, "available": True}
            for i in range(1, 51)
        }
        self.db_calls = 0

    def get_room(self, room_id: str) -> dict:
        time.sleep(0.15)                 # імітація повільного SELECT
        self.db_calls += 1
        return self._db.get(room_id)
