class HotelBookingService:
    def place_booking(self, booking):
        # ... логіка збереження бронювання номера ...

        # Сповіщення "у лоб" -- порушення OCP та SRP
        if booking.guest.wants_email:
            print(f"Sending EMAIL to {booking.guest.email}: booking confirmed")
        if booking.guest.wants_sms:
            print(f"Sending SMS to {booking.guest.phone}: booking confirmed")
        # Аналітику додали окремим патчем прямо тут
        print(f"[ANALYTICS] booking {booking.id} placed, total={booking.total}")

        # Якщо надсилання email не вдалось -- просто мовчки ігноруємо
