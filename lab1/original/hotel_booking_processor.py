class HotelBookingProcessor:
    def process_booking(self, booking, payment_type):
        # 1. Валідація бронювання
        if len(booking.rooms) == 0:
            raise Exception("Booking has no rooms")

        # 2. Розрахунок знижки за типом гостя (порушення OCP)
        discount = 0
        if booking.guest_type == "VIP":
            discount = 0.2
        elif booking.guest_type == "Standard":
            discount = 0.05

        total = sum(room.price for room in booking.rooms) * (1 - discount)

        # 3. Оплата (порушення OCP та DIP)
        if payment_type == "CreditCard":
            print(f"Processing credit card payment for {total}")
            # Stripe API call...
        elif payment_type == "Crypto":
            print(f"Processing crypto payment for {total}")
            # Coinbase API call...

        # 4. Збереження в базу (порушення SRP та DIP)
        print(f"Saving booking {booking.id} to MySQL Database...")

        # 5. Відправка підтвердження (порушення SRP)
        print(f"Sending Email to {booking.guest_email}: Your booking is confirmed.")
