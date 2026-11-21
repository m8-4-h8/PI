from shop.models import Order
from shop.repositories.base import OrderRepository


class MySqlOrderRepository(OrderRepository):
    def save(self, order: Order, total: float) -> None:
        print(f"Saving order {order.id} (total {total}) to MySQL Database...")
