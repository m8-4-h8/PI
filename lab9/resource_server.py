"""Перевірки Resource Server (BookingService) над access_token перед GET /v1/bookings/{id}.

Підпис JWT перевіряє бібліотека (PyJWT/jose) за ключем з JWKS Authorization Server-а
з фіксованим списком алгоритмів (RS256). Сюди приходять уже розібрані claims.
"""
from dataclasses import dataclass

ISSUER = "https://auth.stayhub.example"
AUDIENCE = "booking-api"
REQUIRED_SCOPE = "bookings:read"


class Unauthorized(Exception):
    """401: токен недійсний -- автентифікація не пройшла."""


class Forbidden(Exception):
    """403/404: токен дійсний, але цьому суб'єкту не можна бачити цей ресурс."""


@dataclass(frozen=True)
class Booking:
    id: str
    guest_id: str
    hotel_id: str


def authenticate(claims: dict, now: int) -> None:
    if claims.get("iss") != ISSUER:
        raise Unauthorized("wrong issuer")
    aud = claims.get("aud")
    if AUDIENCE not in (aud if isinstance(aud, list) else [aud]):
        raise Unauthorized("token is not for booking-api")
    if claims.get("exp", 0) <= now or claims.get("nbf", 0) > now:
        raise Unauthorized("token expired or not yet valid")


def authorize_read(claims: dict, booking: Booking) -> None:
    if REQUIRED_SCOPE not in claims.get("scope", "").split():
        raise Forbidden("missing scope bookings:read")
    if claims.get("sub") != booking.guest_id:          # захист від IDOR
        raise Forbidden("booking belongs to another guest")


def get_booking_for(claims: dict, booking: Booking, now: int) -> Booking:
    authenticate(claims, now)
    authorize_read(claims, booking)
    return booking
