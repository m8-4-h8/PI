class OrderService:
    def place_order(self, order):
        # ... логіка збереження замовлення ...

        # Сповіщення "у лоб" -- порушення OCP та SRP
        if order.customer.wants_email:
            print(f"Sending EMAIL to {order.customer.email}: order confirmed")
        if order.customer.wants_sms:
            print(f"Sending SMS to {order.customer.phone}: order confirmed")
        # Аналітику додали окремим патчем прямо тут
        print(f"[ANALYTICS] order {order.id} placed, total={order.total}")

        # Якщо надсилання email не вдалось -- просто мовчки ігноруємо
