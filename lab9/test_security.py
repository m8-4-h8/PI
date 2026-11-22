"""Тести: ін'єкція і перевірки access_token. Запуск: pytest -q (потрібен Flask)."""
import pytest

from resource_server import Booking, Forbidden, Unauthorized, get_booking_for
from support_app import app

PAYLOAD = "' OR '1'='1"
client = app.test_client()


def test_vulnerable_endpoint_leaks_all_guests():
    rows = client.get("/internal/support/guests-vulnerable", query_string={"last_name": PAYLOAD}).get_json()
    assert len(rows) == 5


def test_parameterized_endpoint_returns_nothing_for_payload():
    rows = client.get("/internal/support/guests", query_string={"last_name": PAYLOAD}).get_json()
    assert rows == []


def test_parameterized_endpoint_finds_regular_and_quoted_names():
    assert len(client.get("/internal/support/guests", query_string={"last_name": "Kovalenko"}).get_json()) == 2
    assert len(client.get("/internal/support/guests", query_string={"last_name": "O'Brien"}).get_json()) == 1


def test_vulnerable_endpoint_breaks_on_legit_apostrophe():
    app.config["PROPAGATE_EXCEPTIONS"] = False
    assert client.get("/internal/support/guests-vulnerable", query_string={"last_name": "O'Brien"}).status_code == 500


def test_empty_last_name_rejected():
    assert client.get("/internal/support/guests").status_code == 422


NOW = 1_800_000_000
BOOKING = Booking(id="bk_01", guest_id="guest-42", hotel_id="hotel-7")
GOOD = {"iss": "https://auth.stayhub.example", "aud": "booking-api", "sub": "guest-42",
        "scope": "bookings:read", "exp": NOW + 600, "nbf": NOW - 10, "azp": "partner-analytics"}


def test_valid_token_of_owner_gets_booking():
    assert get_booking_for(GOOD, BOOKING, NOW) == BOOKING


@pytest.mark.parametrize("change", [{"exp": NOW - 1}, {"aud": "payment-api"}, {"iss": "https://evil.example"}])
def test_invalid_token_is_unauthorized(change):
    with pytest.raises(Unauthorized):
        get_booking_for({**GOOD, **change}, BOOKING, NOW)


@pytest.mark.parametrize("change", [{"sub": "guest-7"}, {"scope": "profile:read"}])
def test_valid_token_without_rights_is_forbidden(change):
    with pytest.raises(Forbidden):
        get_booking_for({**GOOD, **change}, BOOKING, NOW)
