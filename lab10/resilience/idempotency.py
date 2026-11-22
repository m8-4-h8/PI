"""Завдання 4.2. POST /payment з Idempotency-Key."""
import hashlib
import json
import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class Response:
    status: int
    body: dict


class FakePaymentGateway:
    """Зовнішній банк. Лічильник фактичних списань."""

    def __init__(self) -> None:
        self.charges = 0

    def charge(self, booking_id: str, amount: str) -> str:
        self.charges += 1
        return f"ch_{self.charges}"


class PaymentEndpoint:
    """Зберігає результат для кожного ключа. У проді -- таблиця з UNIQUE(idempotency_key)
    і TTL 24 год; тут -- словник під замком."""

    def __init__(self, gateway: FakePaymentGateway) -> None:
        self._gateway = gateway
        self._results: dict[str, tuple[str, Response]] = {}
        self._in_progress: set[str] = set()
        self._lock = threading.Lock()

    @staticmethod
    def _fingerprint(body: dict) -> str:
        return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()

    def post_payment(self, idempotency_key: str | None, body: dict) -> Response:
        if not idempotency_key:
            return Response(400, {"error": "Idempotency-Key header is required"})
        fingerprint = self._fingerprint(body)
        with self._lock:
            if idempotency_key in self._results:
                saved_fingerprint, saved = self._results[idempotency_key]
                if saved_fingerprint != fingerprint:   # той самий ключ, інший запит
                    return Response(422, {"error": "Idempotency-Key reused with a different body"})
                return saved                           # повтор -- збережений результат
            if idempotency_key in self._in_progress:   # паралельний дубль ще обробляється
                return Response(409, {"error": "request with this key is in progress"})
            self._in_progress.add(idempotency_key)
        try:
            charge_id = self._gateway.charge(body["booking_id"], body["amount"])
            response = Response(201, {"status": "captured", "charge_id": charge_id,
                                      "booking_id": body["booking_id"], "amount": body["amount"]})
            with self._lock:
                self._results[idempotency_key] = (fingerprint, response)
            return response
        finally:
            with self._lock:
                self._in_progress.discard(idempotency_key)
