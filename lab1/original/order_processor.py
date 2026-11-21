class OrderProcessor:
    def process_order(self, order, payment_type):
        # 1. Валідація замовлення
        if len(order.items) == 0:
            raise Exception("Order is empty")

        # 2. Розрахунок знижки (порушення OCP)
        discount = 0
        if order.customer_type == "VIP":
            discount = 0.2
        elif order.customer_type == "Standard":
            discount = 0.05

        total = sum(item.price for item in order.items) * (1 - discount)

        # 3. Оплата (порушення OCP та DIP)
        if payment_type == "CreditCard":
            print(f"Processing credit card payment for {total}")
            # Stripe API call...
        elif payment_type == "Crypto":
            print(f"Processing crypto payment for {total}")
            # Coinbase API call...

        # 4. Збереження в базу (порушення SRP та DIP)
        print(f"Saving order {order.id} to MySQL Database...")

        # 5. Відправка повідомлення (порушення SRP)
        print(f"Sending Email to {order.customer_email}: Your order is processed.")
